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


def plot_ordered_bar(df, x, y):
    df = df.sort_values(x, ascending=False)
    # Emojis aren't available in the default font, will raise "Glyph missing from current font" errors
    sns.set(style='whitegrid')
    f, ax = plt.subplots()
    sns.barplot(x=x, y=y, data=df,
                palette=sns.color_palette("Blues", n_colors=50),
                order=df[:50]['title'][::-1])
    ax.set(ylim=(0, 50), ylabel=y, xlabel=x)
    sns.despine(left=True, bottom=True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))  # add commas to xlabels


def plot_annotated_scatter(df, x, y, label):
    ax = messenger_data.plot.scatter(x=x, y=y, c='RoyalBlue')
    df[[x, y, label]].apply(lambda x: ax.text(*x), axis=1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))


if __name__ == '__main__':
    # Import data
    messenger_data = pd.DataFrame.from_dict(import_messenger_data('messages')).T.reset_index(drop=True)
    # Plot message length data
    messenger_data['message_lengths'] = messenger_data['messages'].apply(lambda x: len(x))
    plot_ordered_bar(messenger_data, 'message_lengths', 'title')
    # Time Active
    messenger_data['time_active_days'] = messenger_data['messages'].apply(
        lambda x: (x[0]['timestamp_ms'] - x[-1]['timestamp_ms']) / (1000 * 60 * 60 * 24))  # ms to days
    plot_annotated_scatter(messenger_data, 'time_active_days', 'message_lengths', 'title')
    # TODO: Turn off glyph warning
    # TODO: Plot message lengths by group size
    # TODO: Plot velocity 6 months/year/all time vs time active/group size
    # TODO: Friend network by message counts (node size) group chat common members (edges)
    # TODO: Group nodes (friend groups/group chat)
