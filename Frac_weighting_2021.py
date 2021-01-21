#!/usr/bin/python

import os
from osgeo import ogr, gdal
import time
import functions as func

#set the working directory
workingDir=os.path.sep.join(['','Users', 'privateprivate','SAEON','Python_code','Resampling'])
os.chdir(workingDir)
#Make an outputs folder for temporary files in the working directory
func.mkdir_recursive(os.path.sep.join(['outputs', 'temp']))
#define some inputs and outputs
# os.path.sep.join(['outputs', 'temp','raster_clip.tif'])
input_features = os.path.sep.join(['inputs', 'KZN merge.shp']) #the polygon shapefile to resample values into
inputraster=os.path.sep.join(['inputs', 'AboveGroundBiomassWoody_tDM_ha_DEA_CSIR_1.1.10-2015-10-09.tif'])#The raster to resample from
temp_outShapefile=os.path.sep.join(['outputs', 'temp','tempshape.shp'])#a temporary shapefile to represent each polygon
temp_outputraster =  os.path.sep.join(['outputs', 'temp','raster_clip.tif'])#a temporary raster clip for each polygon in the shapefile.
outputShapefile= os.path.sep.join(['outputs', 'KZN_resampled.shp'])#the output polygon shapefile file with resampled values	

def main():
	'''
	This example performs a hi-resolotion resmapling of raster values into a plygon shapefile, see functions.py for details...
	It assumes that the input raster is in an equal area projection in meter units. 
	'''	
	#set the gdal working directory
	gdal.UseExceptions()
	gdal.SetConfigOption("GDAL_DATA", "gdal-data/")
	start_time = time.time()
	help(func.polygon_resample)
	#print the attributes in the shapefile to get one to uise to identify
	attrs_general=func.get_attributes('ESRI Shapefile',input_features,False)
	print(attrs_general);print()#e.g. we will use 'NbalId'
	new_attributes=['CSIR_T','CSIR_Ha','CSIR_T_HA']#In this example, these have to be 3 (total volume, area in Ha, and volume/ha
	#The main function to run
	func.polygon_resample('ESRI Shapefile',input_features,outputShapefile,inputraster,temp_outShapefile,temp_outputraster,new_attributes,'NbalId',1.0)
	print();print("Total runtime took --- %s seconds ---" % (time.time() - start_time))
	
# Execute main() function
if __name__ == '__main__':
	main()


	