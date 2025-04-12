# QGIS Core
from qgis.core import QgsProject

# PyQt
from qgis.PyQt.Qt     import QDateTime
from qgis.PyQt.QtCore import pyqtSlot

# QGIS Utils
from qgis.utils import iface

# Plugin
from .input_check import InputCheck

class QuickCopyPaste:

    def __init__(self, dlg):
        self.iface = iface
        self.msg   = self.iface.messageBar()
        self.chk   = InputCheck()
        self.dlg   = dlg
        self.did_select = False

    @pyqtSlot('QItemSelection', 'QItemSelection')
    def selected_cell(self, selected, deselected):
        active_flag = self.dlg.activatePlugin.isChecked() and self.dlg.enableCopyPaste.isChecked()
        if selected and active_flag:
            OUT_FIELDS = self.dlg.extract_outfields()
            idx        = selected.indexes()[0]
            fld_name   = OUT_FIELDS[idx.column()]
            selval     = idx.data()
    
            if fld_name != 'fid':
                self.copycell(fld_name, selval)
            else:
                self.msg.pushInfo('GetFeats:', 'Cannot modify a field named fid')


    def copycell(self, fld_name, selval):
        TARGET_LYR_NAME = self.dlg.targetLayer.currentLayer().name()
        active_lyr_flag = TARGET_LYR_NAME == self.iface.activeLayer().name()

        if self.chk.check_lyr_valid(TARGET_LYR_NAME) and active_lyr_flag:
            target_lyr = QgsProject.instance().mapLayersByName(TARGET_LYR_NAME)[0]
            edit_flag  = self.chk.check_layer_is_editable(target_lyr)
            open_flag  = self.chk.check_attr_table_open(target_lyr)
            target_ft  = self.chk.check_valid_feature(target_lyr, warn_nofeat = True)

            if edit_flag and open_flag and target_ft:
                target_fld_idx = target_lyr.fields().lookupField(fld_name)
                # Returns -1 if field not found
                if target_fld_idx > -1:
                    oldval = str(target_ft[target_fld_idx])
                    # Paste the data and reload the table
                    target_lyr.dataProvider().changeAttributeValues({target_ft.id(): {target_fld_idx: selval}})

                    # reloadData() deselects the feature, reselect and flag so getfeats doesn't run
                    self.did_select = True
                    target_lyr.dataProvider().reloadData()
                    target_lyr.select(target_ft.id())
                    self.did_select = False

                    # Append to the log page
                    # Color red if it failed for some reason
                    if str(target_lyr.selectedFeatures()[0][target_fld_idx]) == str(selval):
                        color_str = 'color:#b7b0ff;">'
                    else:
                        color_str = 'color:#ff774a;">'

                    logmsg = self.format_log(fld_name, str(target_ft.id()), TARGET_LYR_NAME, 
                                             oldval, selval, color_str)
                    self.dlg.copyPasteLog.append(logmsg)
                else:
                    self.msg.pushInfo('GetFeats:', TARGET_LYR_NAME + ' has no matching field: ' + fld_name)


    def format_log(self, fld_name, fid, TARGET_LYR_NAME, oldval, selval, color_str):
        dt0      = QDateTime.currentDateTime().toString()
        pre_bold = '<span style=" font-weight:600; font-style:bold;'
        dt   = pre_bold + color_str + dt0             + '</span>'
        fld  = pre_bold + '">'      + fld_name        + '</span>'
        fid  = pre_bold + '">fid '  + fid             + '</span>'
        lyr  = pre_bold + '">'      + TARGET_LYR_NAME + '</span>'
        val0 = pre_bold + '">'      + oldval          + '</span>'
        val  = pre_bold + '">'      + selval          + '</span>'
        logmsg = dt + ": " + fld + ' of ' + fid + ' in ' + lyr + ' from ' + val0 + ' to ' + val

        return logmsg


