# QGIS Core
from qgis.core import QgsApplication
from qgis.core import QgsProject

# QGIS Utils
from qgis.utils import iface

class InputCheck:

    def __init__(self):
        self.iface = iface
        self.msg   = self.iface.messageBar()
        self.qapp  = QgsApplication.instance()


    def check_dup_layernames(self, dlg):
        names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
        flag  = len(set(names)) == len(names)
        if flag:
            dlg.activatePlugin.setEnabled(True)
        else:
            dlg.activatePlugin.setChecked(False)
            dlg.activatePlugin.setEnabled(False)
            self.msg.pushInfo('GetFeats:', 'Project contains multiple layers with same name')

        return flag

    def check_dup_outfields(self, OUT_FIELDS):
        flag  = len(set(OUT_FIELDS)) == len(OUT_FIELDS)
        if not flag:
            self.msg.pushInfo('GetFeats:', 'Cannot have duplicate Output fields')

        return flag


    def check_lyr_valid(self, lyr_name):
        lyrs  = QgsProject.instance().mapLayersByName(lyr_name)
        nlyrs = len(lyrs)
        res   = []
        if nlyrs == 1:
            res = lyrs[0]
        elif nlyrs == 0:
            self.msg.pushInfo('GetFeats:', lyr_name + ' not found')
        elif nlyrs > 1:
            self.msg.pushInfo('GetFeats:', 'Multiple layers found named ' + lyr_name)

        return res

    def check_dialog_lyrs_exist(self, dlg, warn_nolyr = True):
        target_present = dlg.targetLayer.currentLayer()
        src_present    = dlg.sourceLayer.currentLayer()

        if (not target_present) and warn_nolyr:
            self.msg.pushInfo('GetFeats:', 'No Target layer selected')
        if (not src_present) and warn_nolyr:
            self.msg.pushInfo('GetFeats:', 'No Source layer selected')

        return target_present and src_present

    def check_attr_table_open(self, lyr):
        open_tables = [x for x in self.qapp.allWidgets() if 'QgsAttributeTableDialog' in x.objectName()]
        flag        = any([lyr.id() in x.objectName() for x in open_tables])
        if not flag:
            self.msg.pushInfo('GetFeats:', lyr.name() + ' attribute table not open')
        return flag

    def check_layer_is_editable(self, lyr):
        flag = lyr.isEditable()
        if not flag:
            self.msg.pushInfo('GetFeats:', lyr.name() + ' not in edit mode')
        return flag

    def check_valid_feature(self, target_lyr, warn_nofeat = False):
        feat_count   = target_lyr.selectedFeatureCount()
        sel_feats    = target_lyr.selectedFeatures()
        pt_coords    = [x.geometry().asPoint() for x in sel_feats]
        unique_geoms = len(set(pt_coords))
    
        target_ft = []
        if 'fid' not in target_lyr.fields().names():
            self.msg.pushInfo('GetFeats:', 'Skipped. No fid field in ' + target_lyr.name())
    
        elif unique_geoms < 1:
            if warn_nofeat:
                self.msg.pushInfo('GetFeats:', target_lyr.name() + ' has no feature selected')
            else:
                pass
    
        elif unique_geoms == 1:
            target_ft = sel_feats[0]
            fid       = target_ft.attribute('fid')
            if not str(fid).isdigit():
                self.msg.pushInfo('GetFeats:', 'Skipped. Selected feature has invalid fid = ' + str(fid))
                target_ft = []
    
            elif target_ft.id() != fid:
                self.msg.pushInfo('GetFeats:', 'Skipped. Feature id = ' + str(target_ft.id()) + ' does not match fid = ' +  str(fid))
                target_ft = []
    
            elif feat_count > 1:
                    self.msg.pushInfo('GetFeats:', 'Selected only the first feature (fid: ' + str(fid) + ')')
    
        elif unique_geoms > 1:
                self.msg.pushInfo('GetFeats:', 'Skipped. Points at multiple locations selected')
    
        return target_ft



