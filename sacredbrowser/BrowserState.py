# This class contains structures which represent the state of the application (at a given time) as far as it is NOT
# contained in the database.
# Change requests are usually initiated by a) a signal from a dependency, b) a method call from the controller.
# Each class sends signals to notify users of data changes. Dependencies within this module are set up in
# setup_browser_state_connections; note that dependencies only exist as signal-slot connections.

# Note that all classes should be treated as singletons. When the current study (or another dependency) is changed,
# the object contents are reset, but the object itself must NOT be deleted. All classes save their own state to the global
# QT settings object.

from . import Application
from . import Utilities

from PyQt5 import QtCore

import collections
import enum
import bisect

BrowserStateCollection = collections.namedtuple('BrowserStateCollection',['current_study','sort_order','db_filter','fields','general_settings'])

# create the (presumably singleton) browser state object
def create_browser_state():         
    current_study = CurrentStudy()
    sort_order = SortOrder()
    db_filter = DbFilter()
    fields = Fields()
    general_settings = GeneralSettings()

    return BrowserStateCollection(current_study=current_study,sort_order=sort_order,db_filter=db_filter,fields=fields,general_settings=general_settings)

def setup_browser_state_connections(bs):
    bs.current_study.study_about_to_be_changed.connect(bs.sort_order.slot_study_about_to_be_changed)
    bs.current_study.study_about_to_be_changed.connect(bs.db_filter.slot_study_about_to_be_changed)
    bs.current_study.study_about_to_be_changed.connect(bs.fields.slot_study_about_to_be_changed)
    bs.current_study.study_about_to_be_changed.connect(bs.general_settings.slot_study_about_to_be_changed)

    bs.current_study.study_changed.connect(bs.sort_order.slot_study_changed)
    bs.current_study.study_changed.connect(bs.db_filter.slot_study_changed)
    bs.current_study.study_changed.connect(bs.fields.slot_study_changed)
    bs.current_study.study_changed.connect(bs.general_settings.slot_study_changed)

    bs.fields.visible_fields_changed.connect(bs.sort_order.slot_visible_fields_changed)


# Current study
class CurrentStudy(QtCore.QObject):
    study_about_to_be_changed = QtCore.pyqtSignal(object) # passes the OLD study, allows to disconnect signals etc.
    # TODO don't like that...
    study_changed = QtCore.pyqtSignal(object) # passed the NEW study

    def __init__(self):
        super().__init__()
        self._study = None

    def set_study(self,new_study):
        self.study_about_to_be_changed.emit(self._study)
        self._study = new_study
        self.study_changed.emit(new_study)

    def get_study(self):
        return self._study


# Order according to which experiments are shown (updated via the sorting dialog, and when a new
# study is loaded)
class SortOrder(QtCore.QObject):
    sort_order_to_be_changed = QtCore.pyqtSignal() # new order, was reset
    sort_order_changed = QtCore.pyqtSignal(list,bool) # new order, was reset

    def __init__(self):
        super().__init__()
        self._available_fields = []
        self._order = [] # order as list, a subset of _available_fields

        self._current_qualified_study_id = None

    def set_available_fields(self,fields,reset=False):
        self.sort_order_to_be_changed.emit()
        self._available_fields = fields
#         if reset:
#             self._order = []
#         else:
        # We always try to maintain the sort order, which is OK since the only change which might
        # require a complete reset is when the study is changed - and that is covered by slot_study_changed
        if 1: 
            # reuse old order as much as possible
            new_order = [ x for x in self._order if x in self._available_fields ]
            self._order = new_order

        self._save_sort_order()
        self.sort_order_changed.emit(self._order,reset)

    def sort_request(self,field,pos):
        assert field in self._available_fields

        self.sort_order_to_be_changed.emit()

        # Change existing order as little as possible. Three cases:
        # 1) field is not in list
        # 2) field is already in list, a) before or b) after the new position

        try:
            old_pos = self._order.index(field)
            # case 2)
            del self._order[old_pos]
            self._order.insert(pos,field)
#             if old_pos < pos:
#                 del self._order[old_pos] 
#                 self._order.insert(pos,field)
#             elif old_pos > pos:
#                 del self._order[old_pos]
#                 self._order.insert(pos,field)
        except ValueError:
            # case 1
            self._order.insert(pos,field)
#             del self._order[-1]

        self._save_sort_order()
        self.sort_order_changed.emit(self._order,False)

    def get_order(self):
        return self._order

    def get_available_fields(self):
        return self._available_fields

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed

    def slot_study_changed(self,study):
        self._current_qualified_study_id = study.qualified_id() if study is not None else None
        self._load_sort_order()

    def slot_visible_fields_changed(self,visible,change_data):
        self.set_available_fields(visible,reset=change_data.tp == Fields.ChangeType.Reset) # likewise emits change signal

    def _save_sort_order(self):
        settings = Application.Application.get_global_settings()
        settings.setValue(self._current_qualified_study_id + '/SortOrder/order',self._order)

    def _load_sort_order(self):
        settings = Application.Application.get_global_settings()
        if self._current_qualified_study_id is not None:
            loaded_order = settings.value(self._current_qualified_study_id + '/SortOrder/order')
            if loaded_order is None:
                loaded_order = []
        else:
            loaded_order = None
        # TODO match this against availabel fields - problem since the signals for the new study and for visible fields might 
        # arrive in any order
        self._order = loaded_order
        self.sort_order_changed.emit(self._order,True)




# Last valid database filter request (updated whenever a new database query is made)
class DbFilter(QtCore.QObject):
    filter_to_be_changed = QtCore.pyqtSignal()
    filter_changed = QtCore.pyqtSignal(str,dict)
    filter_rejected = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self._filter_text = ''
        self._filter_dict = {}
        self._current_qualified_study_id = None

    def try_set_filter_text(self,t):
        try:
            query_dict = Utilities.parse_query(t)
        except ValueError:
            self.filter_rejected.emit()
            return False # for internal use

        # everything ok
        self.filter_to_be_changed.emit()
        self._filter_text = t
        self._filter_dict = query_dict
        self.filter_changed.emit(t,query_dict)
        self._save_filter()

        return True # for internal use

    def get_filter_text(self):
        return self._filter_text

    def get_filter_dict(self):
        return self._filter_dict

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed

    def slot_study_changed(self,study):
        self._current_qualified_study_id = study.qualified_id() if study is not None else None
        self._load_filter()

    def _save_filter(self):
        if self._current_qualified_study_id is None:
            return
        settings = Application.Application.get_global_settings()
        settings.setValue(self._current_qualified_study_id + '/Filter/filter_text',self._filter_text)

    def _load_filter(self):
        settings = Application.Application.get_global_settings()
        if self._current_qualified_study_id is not None:
            loaded_filter_text = settings.value(self._current_qualified_study_id + '/Filter/filter_text')
            res = self.try_set_filter_text(loaded_filter_text)
            if not res:
                self.try_set_filter_text('')  # weird (TODO?)
        else:
            self.try_set_filter_text('')  

# Lists of fields which are displayed in the main experiment list, and which could be displayed but are not.
# Note that each field is a tuple (name,fieldtype).
class Fields(QtCore.QObject):
    # this is not a very readable class, due to the preparations for the QT models (which are not very simple either)

    # we might show config fields and result fields (extendable)
    class FieldType:
        Config = 1
        Result = 2

    # The following signals are intended for the model (a subclass of QAbstractListModel). The change type
    # is self-explaining, the info is 
    # - None in the case of Reset
    # - the changed rows in the case of Content
    # - (position, count) in the case of insert (insert happens BEFORE position, position == len(fields before insert)
    #   means that insert was performed at the end
    # - (position, count) in the case of delete (position is the first row deleted)
    # After the change, the new fields list is also passed
    class ChangeType(enum.Enum):
        Reset = 1
        Content = 2
        Insert = 3
        Remove = 4
    ChangeData = collections.namedtuple('ChangeData',['tp','info'])

    visible_fields_to_be_changed = QtCore.pyqtSignal(ChangeData)
    visible_fields_changed = QtCore.pyqtSignal(list,ChangeData)
    invisible_fields_to_be_changed = QtCore.pyqtSignal(ChangeData)
    invisible_fields_changed = QtCore.pyqtSignal(list,ChangeData)

    def __init__(self):
        super().__init__()
        self._invisible_fields = []
        self._visible_fields = []

        self._current_qualified_study_id = None

    def set_fields(self,invisible,visible):
        # This might be called when new data is loaded, or the study is changed, or fields  are
        # loaded from storage. Note that other functions also change the list of fields.

        # Note the structure of the field lists: each field is (Type, Text)
        for x in invisible:
            assert len(x) == 2
        for x in visible:
            assert len(x) == 2

        invisible = sorted(invisible) # always

        visible_fields_changed = (visible != self._visible_fields)
        invisible_fields_changed = (invisible != self._invisible_fields)

        # emit reset signals
        change_data = self.ChangeData(self.ChangeType.Reset,None)

        if visible_fields_changed:
            self.visible_fields_to_be_changed.emit(change_data)
        if invisible_fields_changed:
            self.invisible_fields_to_be_changed.emit(change_data)

        # perform changes
        if visible is not None:
            self._visible_fields = visible
        if invisible is not None:
            # sort by field type first (so results come at the end)
            self._invisible_fields = invisible

        if visible_fields_changed:
            self.visible_fields_changed.emit(self._visible_fields,change_data)
        if invisible_fields_changed:
            self.invisible_fields_changed.emit(self._invisible_fields,change_data)

        self._save_fields()

    def get_available_fields(self):
        return self._invisible_fields + self._visible_fields

    def get_invisible_fields(self):
        return self._invisible_fields

    def get_visible_fields(self):
        return self._visible_fields

    def available_fields_count(self):
        return len(self._invisible_fields) + len(self._visible_fields)

    def invisible_fields_count(self):
        return len(self._invisible_fields)

    def visible_fields_count(self):
        return len(self._visible_fields)

    def move_up(self,vis_row):
        if vis_row < 1 or vis_row >= len(self._visible_fields):
            return # silently ignore?

        # this function changes the visible fields, required this way to get selection right
        change_data_remove = self.ChangeData(self.ChangeType.Remove,(vis_row - 1,1))
        self.visible_fields_to_be_changed.emit(change_data_remove)
        moved_field = self._visible_fields[vis_row - 1]
        del self._visible_fields[vis_row - 1]
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_remove)

        change_data_insert = self.ChangeData(self.ChangeType.Insert,(vis_row,1))
        self.visible_fields_to_be_changed.emit(change_data_insert)
        self._visible_fields.insert(vis_row,moved_field)
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_insert)

        self._save_fields()

    def move_down(self,vis_row):
        if vis_row < 0 or vis_row >= (len(self._visible_fields) - 1):
            return # silently ignore?

        # this function changes the visible fields, required this way to get selection right
        change_data_remove = self.ChangeData(self.ChangeType.Remove,(vis_row + 1,1))
        self.visible_fields_to_be_changed.emit(change_data_remove)
        moved_field = self._visible_fields[vis_row + 1]
        del self._visible_fields[vis_row + 1]
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_remove)

        change_data_insert = self.ChangeData(self.ChangeType.Insert,(vis_row,1))
        self.visible_fields_to_be_changed.emit(change_data_insert)
        self._visible_fields.insert(vis_row,moved_field)
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_insert)

        self._save_fields()

    def add_visible(self,inv_row,where = None):
        field = self._invisible_fields[inv_row]

        # both lists are going to be changed
        invisible_change_data = self.ChangeData(self.ChangeType.Remove,(inv_row,1))
        visible_change_data = self.ChangeData(self.ChangeType.Insert,(where if where is not None else len(self._visible_fields),1))

        self.invisible_fields_to_be_changed.emit(invisible_change_data)
        self.visible_fields_to_be_changed.emit(visible_change_data)

        del self._invisible_fields[inv_row]
        if where is None:
            self._visible_fields.append(field)
        else:
            self._visible_fields.insert(where,field)

        self.invisible_fields_changed.emit(self.get_invisible_fields(),invisible_change_data)
        self.visible_fields_changed.emit(self.get_visible_fields(),visible_change_data)

        self._save_fields()

    def remove_visible(self,vis_row):
        field = self._visible_fields[vis_row]
        where = bisect.bisect(self._invisible_fields,field) 

        # both lists are going to be changed
        visible_change_data = self.ChangeData(self.ChangeType.Remove,(vis_row,1))
        invisible_change_data = self.ChangeData(self.ChangeType.Insert,(where,1))

        self.invisible_fields_to_be_changed.emit(invisible_change_data)
        self.visible_fields_to_be_changed.emit(visible_change_data)

        self._invisible_fields.insert(where,field)
        del self._visible_fields[vis_row]

        self.invisible_fields_changed.emit(self.get_invisible_fields(),invisible_change_data)
        self.visible_fields_changed.emit(self.get_visible_fields(),visible_change_data)

        self._save_fields()

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed


    def slot_study_changed(self,study):
        # give the fields the format (type, field), this allows to sort naturally
        if study is not None:
            config_fields = [ (Fields.FieldType.Config, x) for x in study.list_config_fields() ]
            result_fields = [ (Fields.FieldType.Result, x) for x in study.list_result_fields() ]
        else:
            config_fields = []
            result_fields = []
        self._current_qualified_study_id = study.qualified_id() if study is not None else None

        self._load_fields(config_fields + result_fields)

    def _save_fields(self):
        if self._current_qualified_study_id is None:
            return
        settings = Application.Application.get_global_settings()
        settings.setValue(self._current_qualified_study_id + '/Fields/visible_fields',self._visible_fields)
        settings.setValue(self._current_qualified_study_id + '/Fields/invisible_fields',self._invisible_fields)

    def _load_fields(self,all_available_fields):
        settings = Application.Application.get_global_settings()

        # try to load from settings, update with data from newly loaded study (may have extra fields...)
        if self._current_qualified_study_id is not None:
            settings = Application.Application.get_global_settings()
            loaded_visible_fields = settings.value(self._current_qualified_study_id + '/Fields/visible_fields')
            loaded_invisible_fields = settings.value(self._current_qualified_study_id + '/Fields/invisible_fields')

            if loaded_visible_fields is not None and loaded_invisible_fields is not None:
                # that worked
                loaded_visible_fields = [ x for x in loaded_visible_fields if x in all_available_fields ]
                loaded_invisible_fields = [ x for x in loaded_invisible_fields if x in all_available_fields ]
                remaining_fields = set(all_available_fields) - (set(loaded_visible_fields) | set(loaded_invisible_fields))
                loaded_visible_fields.extend(remaining_fields)
                self.set_fields(loaded_invisible_fields,loaded_visible_fields)
            else:
                self.set_fields([],all_available_fields)
        else:
            self.set_fields([],[])
# Some general settings, note that they depend on the current study (much like everything else)

class GeneralSettings(QtCore.QObject):
    view_mode_to_be_changed = QtCore.pyqtSignal(int) # new view mode
    view_mode_changed = QtCore.pyqtSignal(int) # new view mode

    column_widths_to_be_changed = QtCore.pyqtSignal(int) # field, new width
    column_widths_changed = QtCore.pyqtSignal(int,int) # field, new width

    ViewModeRaw = 0
    ViewModeRounded = 1
    ViewModePercent = 2

    DefaultColumnWidth = 50

    def __init__(self):
        super().__init__()
        self._view_mode = self.ViewModeRounded
        self._column_widths = {}
        self._current_qualified_study_id = None

    def get_view_mode(self):
        return self._view_mode

    def set_view_mode(self,new_mode):
        self.view_mode_to_be_changed.emit(new_mode)
        self._view_mode = new_mode
        self.view_mode_changed.emit(new_mode)
        self._save_view_mode()

    def get_column_width(self,field):
        return self._column_widths.get(field,DefaultColumnWidth)

    def set_column_width(self,field,width):
        self.column_widths_to_be_changed.emit(field,width)
        self._column_widths[field] = width
        self.column_widths_changed.emit(field,width)
        self._save_column_widths()

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed

    def slot_study_changed(self,study):
        self._current_qualified_study_id = study.qualified_id() if study is not None else None

        self._load_view_mode()
        self._load_column_widths()


    def _save_view_mode(self):
        print('SAving view mode',self._view_mode)
        settings = Application.Application.get_global_settings()
        settings.setValue(self._current_qualified_study_id + '/GeneralSettings/view_mode',self._view_mode)

    def _save_column_widths(self):
        settings = Application.Application.get_global_settings()
        settings.setValue(self._current_qualified_study_id + '/GeneralSettings/column_widths',self._column_widths)

    def _load_view_mode(self):
        settings = Application.Application.get_global_settings()
        if self._current_qualified_study_id is not None:
            loaded_view_mode = settings.value(self._current_qualified_study_id + '/GeneralSettings/view_mode')
            if loaded_view_mode is None:
                loaded_view_mode = self.ViewModeRounded
            else:
                loaded_view_mode = int(loaded_view_mode)
        else:
            loaded_view_mode = self.ViewModeRounded
        print('LOAD VIEW MODE called, is now',loaded_view_mode)


        self.set_view_mode(loaded_view_mode)

    def _load_column_widths(self):
        settings = Application.Application.get_global_settings()
        if self._current_qualified_study_id is not None:
            loaded_column_widths = settings.value(self._current_qualified_study_id + '/GeneralSettings/column_widths')
            if loaded_column_widths is None:
                loaded_column_widths = {}
        else:
            loaded_column_widths = {}

        for field,val in loaded_column_widths.items():
            self.set_column_widths(field,val)

