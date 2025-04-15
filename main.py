# QGIS Core
from qgis.core import QgsProject
from qgis.core import QgsSpatialIndex

# PyQt
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui     import QIcon

# Python
import os.path

# Plugin
from .src.getfeats         import getfeats
from .src.dialog           import PluginDialog
from .src.input_check      import InputCheck
from .src.quick_copy_paste import QuickCopyPaste

class GetFeatsPlugin:

    def __init__(self, iface):
        self.iface      = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg        = PluginDialog()
        self.msg        = self.iface.messageBar()
        self.chk        = InputCheck()
        self.qcp        = QuickCopyPaste(self.dlg)

        self.is_first_run       = True
        self.target_lyr_history = []
        self.source_lyr_last    = []

    def initGui(self):
        icon        = os.path.join(self.plugin_dir, 'img/icon.png')
        self.action = QAction(QIcon(icon), 'GetFeats', self.iface.mainWindow())

        # Add the toolbar
        self.toolbar = self.iface.addToolBar('GetFeats')
        self.toolbar.setObjectName('GetFeats')
        self.action.triggered.connect(self.run)
        self.toolbar.addAction(self.action)

        # Declare dialog connections
        self.dlg.targetLayer.currentIndexChanged.connect(self.check_plugin_enabled)
        self.dlg.sourceLayer.currentIndexChanged.connect(self.check_plugin_enabled)
        self.dlg.activatePlugin.stateChanged.connect(self.check_plugin_enabled)
        self.dlg.selection_model.selectionChanged.connect(lambda a, b: self.qcp.selected_cell(a, b))

        # Create Hotkey
        self.key_action = QAction('GetFeats', self.iface.mainWindow())
        self.iface.registerMainWindowAction(self.key_action, "Ctrl+Alt+I")
        self.iface.addPluginToMenu('&GetFeats', self.key_action)
        self.key_action.triggered.connect(self.run)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu('& GetFeats', self.action)
        self.iface.unregisterMainWindowAction(self.key_action)
        del self.action
        del self.toolbar

    ###############
    ### Methods ###
    ############### 
    def update_src_lyr_hist(self):
        self.source_lyr_last = self.dlg.sourceLayer.currentLayer().name()

    def set_selchanged_conn(self):
        if self.chk.check_dialog_lyrs_exist(self.dlg):
            TARGET_LYR_NAME = self.dlg.targetLayer.currentLayer().name()
            target_lyr      = self.chk.check_lyr_valid(TARGET_LYR_NAME)
            if target_lyr:
                if TARGET_LYR_NAME not in self.target_lyr_history:
                    target_lyr.selectionChanged.connect(self.run_getfeats)
                    self.target_lyr_history.append(TARGET_LYR_NAME)

    def check_plugin_enabled(self):
        self.chk.check_dup_layernames(self.dlg)
        if self.dlg.activatePlugin.isChecked():
            self.set_selchanged_conn()
            self.build_src_spatial_index()


    def build_src_spatial_index(self):
        if self.chk.check_dialog_lyrs_exist(self.dlg):
            SOURCE_LYR_NAME = self.dlg.sourceLayer.currentLayer().name()
            source_lyr      = self.chk.check_lyr_valid(SOURCE_LYR_NAME)
            if source_lyr:
                self.spatial_idx = QgsSpatialIndex(source_lyr.getFeatures(), 
                                   flags = QgsSpatialIndex.Flag.FlagStoreFeatureGeometries)
                self.dlg.update_nnNotes()


    def run_getfeats(self, selected, deselected):
        active_flag   = self.dlg.activatePlugin.isChecked()
        dup_flag      = self.chk.check_dup_layernames(self.dlg)
        dlg_lyrs_flag = self.chk.check_dialog_lyrs_exist(self.dlg)
        did_sel_flag  = self.qcp.did_select
        all_flags     = active_flag and dup_flag and dlg_lyrs_flag and not did_sel_flag

        if not selected and all_flags:
            self.dlg.clear_table(self.dlg.extract_outfields())

        if selected and all_flags:
            TARGET_LYR_NAME = self.dlg.targetLayer.currentLayer().name()
            
            if TARGET_LYR_NAME == self.iface.activeLayer().name():
                SOURCE_LYR_NAME = self.dlg.sourceLayer.currentLayer().name()
        
                SRC_FIELDS0     = self.dlg.extract_sourcefields()
                OUT_FIELDS      = self.dlg.extract_outfields()
                FIELDMAP        = dict(zip(OUT_FIELDS, SRC_FIELDS0))
                MAX_DISTANCE    = self.dlg.maxDistance.value()
                NEIGHBORS       = self.dlg.nNeighbors.value()
                USE_CUSTOM_PREP = self.dlg.customPrep.isChecked()

                if len(SRC_FIELDS0) == len(OUT_FIELDS):
                    source_lyr = self.chk.check_lyr_valid(SOURCE_LYR_NAME)
                    target_lyr = self.chk.check_lyr_valid(TARGET_LYR_NAME)
                    out_flag   = self.chk.check_dup_outfields(OUT_FIELDS)

                    if target_lyr and source_lyr and out_flag:
                        # Extract unduplicated actual fieldnames from the text input
                        SRC_FIELDS = list(set([x for x in SRC_FIELDS0 if x in source_lyr.fields().names()]))
        
                        if SRC_FIELDS:
                            getfeats(self, TARGET_LYR_NAME, SOURCE_LYR_NAME, 
                                     SRC_FIELDS, OUT_FIELDS, FIELDMAP, 
                                     MAX_DISTANCE, NEIGHBORS, USE_CUSTOM_PREP)
                        else:
                            self.msg.pushInfo('GetFeats:', 'No Source Fields found in ' + SOURCE_LYR_NAME)
                else:
                    self.msg.pushInfo('GetFeats:', 'Source and Output fields must have same length')    


    def run(self):
        # Settings stores only the layer name, get those layers if possible
        source_lyr = QgsProject.instance().mapLayersByName(self.dlg.SOURCE_LYR_NAME)
        target_lyr = QgsProject.instance().mapLayersByName(self.dlg.TARGET_LYR_NAME)
        if source_lyr and target_lyr:
        
            # Init Combobox layers
            if self.is_first_run:
                self.dlg.sourceLayer.setLayer(source_lyr[0])
                self.dlg.targetLayer.setLayer(target_lyr[0])

                # Init source field combobox 
                self.dlg.update_source_field_box()
                self.dlg.update_target_field_box()

                self.is_first_run = False

        self.check_plugin_enabled()
        self.dlg.show()
        

 





