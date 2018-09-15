import glob
import json
import os


class DataLoader:
    """
    Load data from Facebook Messenger json download.
    """

    def __init__(self, path):
        """
        Data Structure Initialisation
        :param path: The facebook messenger data folder
        """
        self.message_dict = {}
        for chat in glob.glob('{}/*/message.json'.format(path)):
            with open(chat) as f:
                temp_chat = json.load(f)
                self.message_dict[temp_chat['title']] = temp_chat

        self.stickers_used = len(os.listdir('{}/stickers_used'.format(path)))
