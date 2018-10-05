from __future__ import absolute_import
from __future__ import print_function
import tables

from stormdrain.pipeline import coroutine
from stormdrain.pubsub import get_exchange
from six.moves import zip

class HDF5FlashDataset(object):
    """ Provides an pipeline source for the flash table part of an HDF5Dataset"""
    def __init__(self, h5dataset, target=None):
        self.target=target
        self.h5dataset = h5dataset
        get_exchange('SD_reflow_start').attach(self)
        
    def send(self, msg):
        """ SD_reflow_start messages are sent here """
        if self.target is not None:
            self.target.send(self.h5dataset.flash_data)

class HDF5Dataset(object):
    def __init__(self, h5filename, table_path=None, target=None, mode='r'):
        self.target = target
        
        self.h5file = tables.open_file(h5filename, mode=mode)
        self.table = self.h5file.get_node(table_path)
        self.data = self.table[:]
        
        get_exchange('SD_reflow_start').attach(self)
        
        flash_table_path = table_path.replace('events', 'flashes')
        try:
            self.flash_table = self.h5file.get_node(flash_table_path)
            self.flash_data = self.flash_table[:]
        except tables.NoSuchNodeError:
            self.flash_table = None
            print("Did not find flash data at {0}".format(flash_table_path))
        

    def update_h5(self, colname, coldata, row_ids):
        col = getattr(self.table.cols, colname)
        # this indexing form doesn't work, though the PyTables hints for SQL users indicates it will
        # manager.table[row_ids] = [ (colname,) + tuple(coldata) ]
        for row_id, datum in zip(row_ids, coldata):
            col[row_id] = datum
        self.h5file.flush()
    
    
    @coroutine
    def update(self, index_name="hdf_row_idx", field_names=None):
        """ update the values in self.data using data received.
        
            Also update the HDF5 file, which requires field_names
            
            This function assumes that the shapes of the data are compatible
            and have enough of the same dtype fields to complete the operation.
            If field_names is None, the dtypes must match exactly.
        """
        while True:
            a = (yield)
            indices = a[index_name]
            if field_names is not None:
                # update only one field
                for field_name in field_names:
                    newdata = a[field_name]
                    self.data[field_name][indices] = newdata
                    self.update_h5(field_name, newdata, indices)
            else:
                # update everything
                self.data[indices] = a
                print("Did not update HDF5 file")
                
        
    def send(self, msg):
        """ SD_reflow_start messages are sent here """
        
        # do we send the whole events table, or somehow dynamically determine that?
        
        if self.target is not None:
            self.target.send(self.data)