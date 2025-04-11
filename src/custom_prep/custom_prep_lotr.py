# QGIS Core
from qgis.core import QgsFeature

# QGIS Utils
from qgis.utils import iface

# Python
import re

DIRECTIONS = ['NULL', 'N', 'E', 'S', 'W']

# Prep the table data
# 1. Add a Heading field to manually choose direction of travel
# 2. Set to lowercase except first letter of each word
def custom_prep(clean_lyr):
    # Require the hardcoded fields
    fld_names     = clean_lyr.fields().names()
    flds_required = ['Heading', 'Name', 'Type']
    flag          = set(flds_required).issubset(fld_names)

    if flag:
        # Pad if fewer features than directions (N, E, etc), want these in the same table
        nfeats = clean_lyr.featureCount()
        if nfeats <= len(DIRECTIONS):
            for i in range(1, len(DIRECTIONS) + 1 - nfeats):
                clean_lyr.dataProvider().addFeatures([QgsFeature()])
    
        clean_feats = clean_lyr.getFeatures()
        features    = []
        cnt         = 0
        for f in clean_feats:
            if cnt <= (len(DIRECTIONS) - 1):
                f.setAttribute('Heading', DIRECTIONS[cnt])
                cnt += 1
            for i in ['Name', 'Type']:
                if str(f.attribute(i)) != 'NULL':    
                    newval = str(f.attribute(i)).title()
                else:
                    newval = str(f.attribute(i))
                f.setAttribute(i, newval)
            features.append(f)
    else:
        features = clean_lyr.getFeatures()
        iface.messageBar().pushInfo('GetFeats:', 'Skipped custom prep. Required fields missing.')
    
    return features