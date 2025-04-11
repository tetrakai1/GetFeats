# QGIS Core
from qgis.core import QgsCoordinateTransform
from qgis.core import QgsGeometry
from qgis.core import QgsFeature
from qgis.core import QgsFeatureRequest
from qgis.core import QgsProject
from qgis.core import QgsProcessing
from qgis.core import QgsSettings
from qgis.core import QgsUnitTypes

# QGIS Utils
from qgis.utils import iface

# Python
from importlib.machinery import SourceFileLoader
import os
import processing

# Plugin
from .utils       import make_new_layer
from .input_check import InputCheck

# This script can load from a variable filename
try:
    fname       = QgsSettings().value("GetFeats/customPrepFile", "custom_prep.py")
    module_path = os.path.join(os.path.dirname(__file__), 'custom_prep', fname)
    custom_prep = SourceFileLoader('custom_prep', module_path).load_module()
except:
    pass

def getfeats(obj, TARGET_LYR_NAME, SOURCE_LYR_NAME, SRC_FIELDS, OUT_FIELDS, FIELDMAP, 
             MAX_DISTANCE, NEIGHBORS, USE_CUSTOM_PREP):
    target_lyr = QgsProject.instance().mapLayersByName(TARGET_LYR_NAME)[0]
    target_ft  = InputCheck.check_valid_feature(obj, target_lyr)
    if target_ft:

        # Find the nearest neighbors
        source_lyr     = QgsProject.instance().mapLayersByName(SOURCE_LYR_NAME)[0]
        source_lyr_crs = source_lyr.crs()
        target_lyr_crs = target_lyr.crs()
        tr   = QgsCoordinateTransform(target_lyr_crs, source_lyr_crs, QgsProject.instance())
        geom = QgsGeometry(target_ft.geometry())
        geom.transform(tr)
        
        src_units = QgsUnitTypes.toString(source_lyr_crs.mapUnits())
        mult      = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceUnit(0), source_lyr_crs.mapUnits())
        max_dist  = MAX_DISTANCE*mult
        nns       = obj.spatial_idx.nearestNeighbor(geom, neighbors = NEIGHBORS, maxDistance = max_dist)

        if obj.dlg.selectFeats.isChecked():
            if obj.source_lyr_last:
                old_src_lyr = QgsProject.instance().mapLayersByName(obj.source_lyr_last)[0]
                old_src_lyr.removeSelection()
            source_lyr.selectByIds(nns)
            obj.update_src_lyr_hist()


        # Extract the deesignated output fields and put into new layer
        # Need this ordered by distance, but getFeatures reorders by fid, so do it the slow way
        extracted_lyr = make_new_layer('extracted_lyr', OUT_FIELDS) 
        features = []
        for fid in nns:
            f = next(source_lyr.getFeatures(QgsFeatureRequest().setFilterFid(fid)))
            newfeat = QgsFeature(extracted_lyr.fields())
            for fld in OUT_FIELDS:
                if FIELDMAP[fld] in SRC_FIELDS:
                    newfeat[fld] = f[FIELDMAP[fld]]
                else:
                    newfeat[fld] = FIELDMAP[fld]

            features.append(newfeat)

        extracted_lyr.dataProvider().addFeatures(features)

        # Delete duplicate rows
        alg_params = {
            'FIELDS': OUT_FIELDS,
            'INPUT' : extracted_lyr,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        clean_lyr = processing.run('native:removeduplicatesbyattribute', alg_params)['OUTPUT']

        # Custom data prep is done here, see custom_prep.py
        if USE_CUSTOM_PREP:
            try:
                features = custom_prep.custom_prep(clean_lyr)
            except:
                iface.messageBar().pushInfo('GetFeats:', 'Error in custom prep. Skipping that step.')
                features = clean_lyr.getFeatures()
        else:
            features = clean_lyr.getFeatures()

        # Update table in plugin dialog
        obj.dlg.update_table(OUT_FIELDS, features)
 
