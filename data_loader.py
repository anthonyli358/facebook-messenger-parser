import json


class DataLoader:
    """
    Load data from Facebook Messenger json download.
    """

    def __init__(self, file):
        """
        Data Structure Initialisation
        :param file: The file to import
        """
        with open(file) as f:
            self.data = json.load(f)
