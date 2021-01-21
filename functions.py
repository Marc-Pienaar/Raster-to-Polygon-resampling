#!/usr/bin/python

import os
from osgeo import gdal, ogr, osr,gdalconst,gdal_array
import time
import pathlib
import shutil

#the main run function
def polygon_resample(driverName,input_features,outputShapefile,inputraster,temp_outShapefile,temp_outputraster,new_attributes,att_name,meters):
	
	"""	
	Author Marc Pienaar, marc.pienaar@gmail.com

	Perform a hi-resolution resmapling (1m) of values from a equal area raster into a polygon shapefile
	Parameters
	----------
	driverName:  String
		The gdal driver name (e.g. "ESRI Shapefile")

	input_features : file or string
		input shapefile name to read.

	outputShapefile: file or string
		The output shapefile name to write to.
	
	inputraster:  Geotiff
		The input raster to reasample from

	temp_outShapefile:  file or string
		A temporary shapefile, respresenting each polygon to write to file for raster cropping

	temp_outputraster:  Geotiff
		A temporary raster to write to file
		
	
	new_attributes: array []
		A vector of thjree array names to add as attributes to the shapefile, e.g. ['Tonne,'Ha',t/ha']

	att_name: A attribute value to print for trouble shooting from the input shapefile
		e.g. geometry = feature.GetGeometryRef() 

	meters: Real or double
		A value representing how high the resmapling resolution should be e.g 1.0=1 meter
		
	Returns:
	-------
	A polygon shapefile	with values from the input raster resmapled into it. 	
	"""
	
	drv = ogr.GetDriverByName(driverName)
	dataSource_in = drv.Open(input_features, 0)  # 0 means read-only. 1 means writeable.
	layer = dataSource_in.GetLayer(0)
	featureCount = layer.GetFeatureCount()#the number of features
	targetprj = layer.GetSpatialRef()  #
	inLayerDefn = layer.GetLayerDefn()# the input file layer definition	
	#create the output shapefile
	outDriver = ogr.GetDriverByName("ESRI Shapefile")
	outDataSet = outDriver.CreateDataSource(outputShapefile)
	outLayer = outDataSet.CreateLayer("temp",targetprj,geom_type=ogr.wkbMultiPolygon)
	#Map the attribute names from the input shapefile to the output shapefile
	for i in range(0, inLayerDefn.GetFieldCount()):
		fieldDefn = inLayerDefn.GetFieldDefn(i)
		outLayer.CreateField(fieldDefn)
	#create additional attributes for resampling 
	for i in new_attributes:
		outLayer.CreateField(ogr.FieldDefn(i, ogr.OFTReal))
	outLayerDefn = outLayer.GetLayerDefn()
	accum=0#To accumulate errors
	for i in range(0, featureCount): # e.g. E154 100 for 0
		feature = layer.GetFeature(i)
		attrs = feature.GetField(att_name)	
		try:
			print(i, 'of',featureCount,'polygons complete: - ID:', attrs)
			geometry = feature.GetGeometryRef()
			# Create the temporary output shapefile
			create_temp_poly(temp_outShapefile,targetprj,geometry)
			#hi-res crop of the raster to the feature 
			hirescrop(inputraster,temp_outputraster,temp_outShapefile,targetprj,geometry,meters,False)
			#creeate two variables to use to accumulate values
			sum = 0;ha=0
			dataset = gdal.Open(temp_outputraster)
			#get a histogram of the values from the cropped raster
			hist = dataset.GetRasterBand(1).GetHistogram(approx_ok = 0)
			for k in range(len(hist)):
				ha=ha+hist[k]
				sum=sum+((k*0.0001)*hist[k])
			#close the temporary raster to free resources
			dataset=None
	#			print(i,featureCount, sum, ha/10000)
			outFeature = ogr.Feature(outLayerDefn)
			outFeature.SetGeometry(geometry)
			#map the original features to the new shapefile
			for j in range(0, inLayerDefn.GetFieldCount()):
				outFeature.SetField(inLayerDefn.GetFieldDefn(j).GetNameRef(), feature.GetField(j))
			#map the new features and values
			outFeature.SetField(new_attributes[0], sum)
			outFeature.SetField(new_attributes[1], ha/10000)
			try:#in case of div/zero
				outFeature.SetField(new_attributes[2], sum/(ha/10000))
			except:
				outFeature.SetField(new_attributes[2], 0.0)
			outLayer.CreateFeature(outFeature)
			outFeature = None	
		except:
			accum=accum+1
			print(accum,attrs,"Error")
	#write and release resources
	outDataSet.Destroy() 
	dataSource_in.Destroy() 
	#delete the temporary folder and outputs
	shutil.rmtree(os.path.sep.join(['outputs', 'temp']))
	

def mkdir_recursive(path):
	"""	
	create a directory and its sub-directories
	Parameters
	----------
	path:  String
		the directory path to create

	Returns
	-------
	Null, creates the directories		
	"""
	if not os.path.exists(path):
		pathlib.Path(path).mkdir(parents=True, exist_ok=True)
		
def get_attributes(drivername, shp_in,showtime):
	"""	
	Get the field names and feature count from a shapefile
	Parameters
	----------
	drivername:  String
		Ogr driver name to handle the file e.g. ESRI_Shapefile or GPKG
		
	shp_in : file or string
		File, directory, or filename to read.

	showtime :  bool
		If True, prints the time this function took to run.
		If False, prints nothing.
	
	Returns
	-------
	Dictionary object:  'attributes' and 'number of features'		
	"""
	if showtime:
		start_time = time.time()
	attrs=[]
	Dict={}
	shpDriver = ogr.GetDriverByName(drivername)
	source_ds = ogr.Open(shp_in)  # open the resource
	layer = source_ds.GetLayer()
	featureCount = layer.GetFeatureCount()
	layerDefinition = layer.GetLayerDefn()
	accum=0	
	for i in range(layerDefinition.GetFieldCount()):
		temp=[]
		temp.append(accum)
		temp.append(layerDefinition.GetFieldDefn(i).GetName())
		accum+=1
		attrs.append(temp)
	Dict['attributes']=attrs
	Dict['number of features']=featureCount
	source_ds=None
	if showtime:
		print("Get attributes from file took --- %s seconds ---" % (time.time() - start_time))
		print()#print a new line
	return(Dict)

def hirescrop(inputraster,outputraster,shpin,targetprj,geometry,meters,showtime):
	"""	
	Perform a hi-resolution crop of a raster, using a shapefile geometry. Then resmaple the raster to 1 unit (e.g. 1m if equal area)
	Parameters
	----------
	inputraster:  Geotiff
		The original rater to crop

	outputraster:  Geotiff
		The output croped geotiff
		
	shp_in : file or string
		File, directory, or filename to read to use as a cutline for gdal warp.

	targetprj: The spatial reference to use for the output raster (e.g. wgs84)
		e.g. layer.GetSpatialRef()

	geometry: The geomtery of the polygon to use for cropping
		e.g. geometry = feature.GetGeometryRef() 
	
	meters: Real or double
		A value representing how high the resmapling resolution should be e.g 1.0=1 meter
	
	showtime :  bool
		If True, prints the time this function took to run.
		If False, prints nothing.
	
	Returns
	-------
	writes out a cropped raster		
	"""
	if showtime:
		start_time = time.time()
	#create two laters in memory 
	(minXl, maxXl, minYl, maxYl) = geometry.GetEnvelope()
	temp_raster = '/vsimem/temp_raster.tif'#write to memory
	temp_raster2 = '/vsimem/temp_raster2.tif'#write to memory
	ds = gdal.Open(inputraster)
	geotransform = ds.GetGeoTransform()	
	x_min, xres, xskew, y_max, yskew, yres = geotransform
	x_max = x_min + (ds.RasterXSize * xres)
	y_min = y_max + (ds.RasterYSize * yres)
	x_res = ds.RasterXSize
	y_res = ds.RasterYSize
	pixel_width = xres	
	temp_buffer = max(geotransform[5], abs(geotransform[5]))
	prj = ds.GetProjection()
	sourceprj = osr.SpatialReference(wkt=prj)
	ds = None
	transform = osr.CoordinateTransformation(targetprj, sourceprj)
	# get extent of target layer in source projection
	minX, maxY = transform.TransformPoint(minXl, maxYl)[0:2]
	maxX, minY = transform.TransformPoint(maxXl, minYl)[0:2]
	# use gdal.translate to clip the raster + add a small buffer to ensure that we return overlapping areas
	out_ds = gdal.Translate(temp_raster,inputraster,projWin=[minX - temp_buffer, maxY + temp_buffer,maxX + temp_buffer,minY - temp_buffer])
	out_ds = None
	#resample down to a single unit (e..g meters)
	out_ds = gdal.Translate(temp_raster2, temp_raster,format='GTiff', xRes=meters, yRes=meters)
	out_ds = None  # release resources
	# now apply the new projection
	out_ds = gdal.Warp(temp_raster, temp_raster2, dstSRS=targetprj,cutlineDSName=shpin)	
	out_ds = None
	##reclip and add a small 5% buffer around the shapefile
	x_buf=abs(maxXl-minXl)*0.05
	y_buf=abs(maxYl-minYl)*0.05	
	out_ds = gdal.Translate(outputraster,temp_raster,projWin=[minXl-x_buf, maxYl+x_buf, maxXl+y_buf, minYl-y_buf])  	
	out_ds = None
	if showtime:
		print("Hi-res cropping took --- %s seconds ---" % (time.time() - start_time))
		print()#print a new line

def create_temp_poly(temp_outShapefile,targetprj,geometry):
	"""	
	Perform a hi-resolution crop of a raster, using a shapefile geometry. Then resmaple the raster to 1 unit (e.g. 1m if equal area)
	Parameters
	----------
	temp_outShapefile:  filename
		a temporary shapefile name to write to

	targetprj: The spatial reference to use for the output raster (e.g. wgs84)
		e.g. layer.GetSpatialRef()

	geometry: The geomtery of the polygon to use for cropping
		e.g. geometry = feature.GetGeometryRef() 
		
	Returns:
	-------
	writes out a temporay shapefile		
	"""
	
	outDriver = ogr.GetDriverByName("ESRI Shapefile")
	outDataSource = outDriver.CreateDataSource(temp_outShapefile)
	outLayer = outDataSource.CreateLayer("outline", targetprj,geom_type=ogr.wkbPolygon)
	# Add an ID field
	idField = ogr.FieldDefn("id", ogr.OFTInteger)
	outLayer.CreateField(idField)
	featureDefn = outLayer.GetLayerDefn()
	outfeature = ogr.Feature(featureDefn)
	outfeature.SetGeometry(geometry)
	outfeature.SetField("id", 1)
	outLayer.CreateFeature(outfeature)
	# Close DataSource
	outDataSource.Destroy()