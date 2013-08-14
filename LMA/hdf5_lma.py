import tables

from stormdrain.pipeline import coroutine
from stormdrain.pubsub import get_exchange

class HDF5Dataset(object):
    def __init__(self, h5filename, table_path=None, target=None, mode='r'):
        self.target = target
        
        self.h5file = tables.openFile(h5filename, mode=mode)
        self.table = self.h5file.getNode(table_path)
        self.data = self.table[:]
        
        self.bounds_updated_xchg = get_exchange('SD_bounds_updated')
        self.bounds_updated_xchg.attach(self)        

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
                print "Did not update HDF5 file"
                
        
    def send(self, msg):
        """ SD_bounds_updated messages are sent here """
        
        # do we send the whole events table, or somehow dynamically determine that?
        
        if self.target is not None:
            self.target.send(self.data)