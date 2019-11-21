import glob
import json
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter


def import_messenger_data(path):
    message_dict = {}
    for chat in glob.glob(f'{path}/*/message.json'):
        with open(chat) as f:
            temp_chat = json.load(f)
            message_dict[temp_chat['title']] = temp_chat
    return message_dict


def plot_ordered_bar(df):
    df = df.sort_values('message_lengths', ascending=False)
    # Emojis aren't available, will raise "Glyph missing from current font" errors
    sns.set(style='whitegrid')
    f, ax = plt.subplots()
    sns.barplot(x='message_lengths', y='title', data=df,
                palette=sns.color_palette("Blues_d", n_colors=50),
                order=df[:50]['title'][::-1])
    ax.set(ylim=(0, 50), ylabel='Chat', xlabel='Message Lengths')
    sns.despine(left=True, bottom=True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))  # add commas to xlabels


if __name__ == '__main__':
    # Import data
    messenger_data = pd.DataFrame.from_dict(import_messenger_data('messages')).T.reset_index(drop=True)
    # Plot message length data
    messenger_data['message_lengths'] = messenger_data['messages'].apply(lambda x: len(x))
    plot_ordered_bar(messenger_data)
