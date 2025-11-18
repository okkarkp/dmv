from patch_excel_reader import load_dmw_sheet

def load_file(path, sheet="Baseline Data Model"):
    """
    Wrapper for DMW sheet loading.
    """
    return load_dmw_sheet(path, sheet)
