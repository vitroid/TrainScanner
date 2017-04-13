import argparse
import logging

class MyArgumentParser(argparse.ArgumentParser):
    """
    Override the following function in order to leave the "fromfile" filename.
    """
    def __init__(self, **args):
        super(MyArgumentParser, self).__init__(self, **args)
        self.fromfile_name = None
        
    def _read_args_from_files(self, arg_strings):
        for arg_string in arg_strings:
            # for regular arguments, just add them back into the list
            if not arg_string or arg_string[0] not in self.fromfile_prefix_chars:
                pass
            # replace arguments referencing files with the file content
            else:
                self.fromfile_name = arg_string[1:]

        return super()._read_args_from_files(arg_strings)
