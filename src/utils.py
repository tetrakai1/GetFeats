# QGIS Core
from qgis.core import QgsField
from qgis.core import QgsVectorLayer

# PyQt
from qgis.PyQt.QtCore import QMetaType

# Python
from math import cos
from math import pi

# Make a new layer with the provided name and string fields
def make_new_layer(name, OUT_FIELDS):
    new_layer = QgsVectorLayer('Point', name, 'memory')
    provider  = new_layer.dataProvider()

    for fld in OUT_FIELDS:
        provider.addAttributes([QgsField(fld, QMetaType.Type.QString)])

    new_layer.updateFields()

    return new_layer

def est_degree_error(lat, max_dist):
    lat_rad       = lat*pi/180 
    m_per_deg_lat = 111132.954 - 559.822 * cos( 2.0 * lat_rad ) + 1.175 * cos( 4.0 * lat_rad)
    m_per_deg_lon = (3.14159265359/180 ) * 6367449 * cos( lat_rad )
    
    lat_err = max_dist*(1 - m_per_deg_lat/111132.954)
    lon_err = max_dist*(1 - m_per_deg_lon/111132.954)

    return [round(lat_err, 1), round(lon_err, 1)]