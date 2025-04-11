# QGIS Utils
from qgis.utils import iface

# Prep the table data
def custom_prep(clean_lyr):

    features = clean_lyr.getFeatures()
    iface.messageBar().pushInfo('GetFeats:', 'Custom prep script run successfully.')
 
    return features