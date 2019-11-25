import glob
import json
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
import datetime
from collections import Counter
import networkx as nx
from config import config  # mask name in separate file


def import_messenger_data(path):
    message_dict = {}
    for chat in glob.glob(f'{path}/*/message.json'):
        with open(chat) as f:
            temp_chat = json.load(f)
            message_dict[temp_chat['title']] = temp_chat
    return message_dict


def plot_ordered_bar(df, x, y, slice=50, annotate=True):
    df = df.sort_values(x, ascending=False)
    # Emojis aren't available in the default font, will raise 'Glyph missing from current font' errors
    ax = sns.barplot(x=x, y=y, data=df,
                     palette=sns.color_palette('Blues', n_colors=slice),
                     order=df[:slice]['title'][::-1])
    ax.set(ylim=(0, 50), ylabel=y, xlabel=x)
    sns.despine(left=True, bottom=True)
    # ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))  # add commas to xlabels
    if not annotate:
        ax.get_yaxis().set_visible(False)
    plt.show()


def plot_annotated_scatter(df, x, y, label, logx=False, logy=False, annotate=True):
    ax = sns.scatterplot(x=x, y=y, data=df)
    if logx:
        ax.set_xscale('log')
        ax.set_xlim(left=1)
        plt.xlabel('log(time_active_days)')
    if logy:
        ax.set_yscale('log')
        plt.ylabel('log(messages/participants)')
    if not (logx and logy):
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
    if annotate:
        df[[x, y, label]].apply(lambda x: ax.text(*x), axis=1)
    plt.show()


def messages_by_month(df, self=False):
    title, month, month_messages = [], [], []
    for index, row in df.iterrows():
        temp_dict = {}
        participants = len(row['participants']) if isinstance(row['participants'], list) else 1
        for message in row['messages']:
            curr_month = datetime.datetime.fromtimestamp(message['timestamp_ms'] / 1000).strftime('%Y-%m')
            if self is False or (self is True and message['sender_name'] == config['name']):
                if curr_month in temp_dict:
                    temp_dict[curr_month] += 1
                else:
                    temp_dict[curr_month] = 1
        for k, v in temp_dict.items():
            title.append(row['title'] if self is False else config['name'])
            month.append(k)
            month_messages.append(v // participants if self is False else v)
    month_messages_df = pd.DataFrame({'title': title, 'month': month, 'month_messages/participants': month_messages})
    month_messages_df['month'] = pd.to_datetime(month_messages_df['month'], format='%Y-%m')
    return month_messages_df


def plot_annotated_month_data(df, x, y, label, annotate=True):
    ax = sns.lineplot(x=x, y=y, data=df, hue=label if len(df[label].unique()) > 1 else None, legend=False,
                      palette=sns.color_palette('RdBu', n_colors=len(df[label].unique())))
    if annotate:
        to_annotate = df[df.groupby(label)[y].transform(max) == df[y]]
        to_annotate = to_annotate.groupby(label).first()  # take first by group in case of duplicates
        for index, row in to_annotate.iterrows():
            plt.gca().annotate(index, xy=(row[x], row[y]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
    plt.xlabel('year')  # seaborn automatically simplified the month
    # plt.xticks(rotation=90)
    plt.show()


def create_network_df(df):
    name, connections, messages = [], [], []
    for index, row in df.iterrows():
        message_counter = Counter([message['sender_name'] for message in row['messages']])
        if isinstance(row['participants'], list):  # deal with deleted groups
            for i in range(len(row['participants'])):
                name.extend([row['participants'][i]['name']] * (len(row['participants']) - 1))
                connections.extend([i['name'] for i in row['participants'][0:i] + row['participants'][i+1:]])
                messages.extend([message_counter[row['participants'][i]['name']]] * (len(row['participants']) - 1))
    network_df = pd.DataFrame({'name': name, 'connections': connections, 'messages': messages})
    network_df = network_df.groupby(['name', 'connections']).sum().reset_index()
    return network_df


if __name__ == '__main__':
    annotate_plots = False
    # Import data
    messenger_data = pd.DataFrame.from_dict(import_messenger_data('messages')).T.reset_index(drop=True)
    pd.plotting.register_matplotlib_converters()  # temporary fix to register converters
    # Plot message length data
    messenger_data['message_lengths'] = messenger_data['messages'].apply(lambda x: len(x))
    plot_ordered_bar(messenger_data, 'message_lengths', 'title', slice=50, annotate=annotate_plots)
    # Time active
    messenger_data['messages/participants'] = messenger_data['message_lengths'] / messenger_data['participants'].apply(
        lambda x: len(x) if isinstance(x, list) else 1)
    messenger_data['time_active_days'] = messenger_data['messages'].apply(
        lambda x: (x[0]['timestamp_ms'] - x[-1]['timestamp_ms']) / (1000 * 60 * 60 * 24))  # ms to days
    messenger_data['time_active_days_log'] = messenger_data['time_active_days'].apply(
        lambda x: 1.001 if x < 1.001 else x)  # Account for cases with invalid log(time_active_days)
    plot_annotated_scatter(messenger_data, 'time_active_days', 'messages/participants', 'title',
                           annotate=annotate_plots)
    plot_annotated_scatter(messenger_data, 'time_active_days_log', 'messages/participants', 'title',
                           logx=True, logy=True, annotate=annotate_plots)
    # Messages by month
    month_data = messages_by_month(messenger_data).fillna(0)
    plot_annotated_month_data(month_data, 'month', 'month_messages/participants', 'title', annotate=annotate_plots)
    # Self messages by month
    self_month_data = messages_by_month(messenger_data, self=True).fillna(0)
    self_month_data = self_month_data.groupby(['month']).sum().reset_index()
    self_month_data['title'] = config['name']
    plot_annotated_month_data(self_month_data, 'month', 'month_messages/participants', 'title', annotate=False)
    # Network plot
    network_df = create_network_df(messenger_data)
    # TODO: Friend network by message counts (node size) group chat common members (edges)
    # TODO: Directed graph or how to deal with messages both ways
    # TODO: Node size ~log(number of messages)
    # TODO: Group nodes (friend groups/group chat)
