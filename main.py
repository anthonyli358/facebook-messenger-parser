import datetime
import glob
import json
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns
from collections import Counter
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from config import config  # mask name in separate file


def import_messenger_data(path, split=True):
    message_dict = {}
    for chat in glob.glob(f'{path}/*/message_*.json'):
        with open(chat) as f:
            temp_chat = json.load(f)
            if split:  # new facebook messenger data splits messages into multiple json files
                if temp_chat['title'] in message_dict:
                    message_dict[temp_chat['title']]['messages'].extend(temp_chat['messages'])
                else:
                    message_dict[temp_chat['title']] = temp_chat
            else:
                message_dict[temp_chat['title']] = temp_chat
    return message_dict


def clean_messenger_data(df):
    df['participants'] = df['participants'].apply(lambda x: x if isinstance(x, list) else [])  # self-messages
    df['participants'] = df['participants'].apply(lambda x: [{'name': config['name']}] if len(x) < 1 else x)
    return df


def features_messenger_data(df):
    df['message_lengths'] = df['messages'].apply(lambda x: len(x))
    df['messages/participants'] = df['message_lengths'] / df['participants'].apply(
        lambda x: len(x))
    df['time_active_days'] = df['messages'].apply(   # ms to days
        lambda x: (max([i['timestamp_ms'] for i in x]) - min([i['timestamp_ms'] for i in x])) / (1000 * 60 * 60 * 24))
    df['time_active_days_log'] = df['time_active_days'].apply(
        lambda x: 1.001 if x < 1.001 else x)  # account for cases with invalid log(time_active_days)
    return df


def plot_ordered_bar(df, x, y, slice=50, annotate=True):
    df = df.sort_values(x, ascending=False)
    # Emojis aren't available in the default font, will raise 'Glyph missing from current font' errors
    f, ax = plt.subplots()
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
    f, ax = plt.subplots()
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
            month_messages.append(v // len(row['participants']) if self is False else v)
    month_messages_df = pd.DataFrame({'title': title, 'month': month, 'month_messages/participants': month_messages})
    month_messages_df['month'] = pd.to_datetime(month_messages_df['month'], format='%Y-%m')
    month_messages_df.fillna(0, inplace=True)
    return month_messages_df


def plot_annotated_month_data(df, x, y, label, annotate=True):
    f, ax = plt.subplots()
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


def create_network_df(df, slice=50, group=False):
    df['message_lengths'] = df['messages'].apply(lambda x: len(x))
    df = df.sort_values(['message_lengths'], ascending=False)
    df = df[:slice]  # limit nodes to avoid overcrowding
    name, connections, messages = [], [], []
    for index, row in df.iterrows():
        message_counter = Counter([message['sender_name'] for message in row['messages']])
        participants = len(row['participants'])
        if group:
            if participants > 2:  # group chats only
                for i in range(len(row['participants'])):
                    name.append(row['participants'][i]['name'])
                    connections.append(row['title'])
                    messages.append(message_counter[row['participants'][i]['name']])
        else:
            for i in range(len(row['participants'])):
                name.extend([row['participants'][i]['name']] * (len(row['participants']) - 1))
                connections.extend([i['name'] for i in row['participants'][0:i] + row['participants'][i + 1:]])
                messages.extend([message_counter[row['participants'][i]['name']]] * (len(row['participants']) - 1))
    network_df = pd.DataFrame({'name': name, 'connections': connections, 'messages': messages})
    network_df = network_df.groupby(['name', 'connections']).sum().reset_index()
    return network_df


def plot_network(df, seed=None, annotate=True, group=False):
    plt.figure()
    graph = nx.from_pandas_edgelist(df, source='name', target='connections', edge_attr='messages')
    layout = nx.spring_layout(graph, seed=seed)
    nx.draw_networkx_edges(graph, layout, edge_color='#AAAAAA')
    if group:
        connections = [node for node in graph.nodes() if node in df['connections'].unique()]
        weights = [np.log(graph.degree(node, weight='messages') / graph.degree(node)) * 200 for node in connections]
        nx.draw_networkx_nodes(graph, layout, nodelist=connections, node_size=weights, node_color='lightblue')

        people = [node for node in graph.nodes() if node in df['name'].unique()]
        nx.draw_networkx_nodes(graph, layout, nodelist=people, node_size=100, node_color='RoyalBlue')

        high_degree_people = [node for node in graph.nodes() if node in df['name'].unique() and graph.degree(node) > 1]
        nx.draw_networkx_nodes(graph, layout, nodelist=high_degree_people, node_size=100, node_color='#fc8d62')  # orange
        if annotate:
            connection_dict = dict(zip(connections, connections))
            nx.draw_networkx_labels(graph, layout, labels=connection_dict)
    else:
        people = [node for node in graph.nodes() if node in df['name'].unique() and graph.degree(node) <= 1]
        people_weights = [np.log(max(graph.degree(node, weight='messages'), 1)) * 25 for node in people]
        nx.draw_networkx_nodes(graph, layout, nodelist=people, node_size=people_weights, node_color='RoyalBlue')

        high_degree_people = [node for node in graph.nodes() if node in df['name'].unique() and graph.degree(node) > 1]
        high_degree_people_weights = [np.log(max(graph.degree(node, weight='messages'), 1)) * 25
                                      for node in high_degree_people]
        nx.draw_networkx_nodes(graph, layout, nodelist=high_degree_people, node_size=high_degree_people_weights,
                               node_color='#fc8d62')  # orange
        if annotate:
            people_nodes = [node for node in graph.nodes() if node in df['name'].unique()]
            people_dict = dict(zip(people_nodes, people_nodes))
            nx.draw_networkx_labels(graph, layout, labels=people_dict)
    plt.axis('off')
    plt.title('Facebook Messenger Network')
    plt.show()


if __name__ == '__main__':
    # Annotate plots with chat titles?
    annotate_plots = True

    # Import data
    messenger_data = pd.DataFrame.from_dict(import_messenger_data('messages')).T.reset_index(drop=True)
    messenger_data = clean_messenger_data(messenger_data)
    messenger_data = features_messenger_data(messenger_data)
    pd.plotting.register_matplotlib_converters()  # temporary fix to register converters

    # Plot message length data
    plot_ordered_bar(messenger_data, 'message_lengths', 'title', slice=50, annotate=annotate_plots)

    # Messages vs active time
    plot_annotated_scatter(messenger_data, 'time_active_days', 'messages/participants', 'title',
                           annotate=annotate_plots)
    plot_annotated_scatter(messenger_data, 'time_active_days_log', 'messages/participants', 'title',
                           logx=True, logy=True, annotate=annotate_plots)

    # Messages by month
    month_data = messages_by_month(messenger_data)
    plot_annotated_month_data(month_data, 'month', 'month_messages/participants', 'title', annotate=annotate_plots)

    # Messages by month rolling average
    month_data['month_messages_roll_av'] = month_data.groupby('title')['month_messages/participants'].transform(
        lambda x: x.rolling(3, 1).mean())
    plot_annotated_month_data(month_data, 'month', 'month_messages_roll_av', 'title', annotate=annotate_plots)

    # Self messages by month
    self_month_data = messages_by_month(messenger_data, self=True)
    self_month_data = self_month_data.groupby(['month']).sum().reset_index()
    self_month_data['title'] = config['name']
    self_month_data.rename(columns={'month_messages/participants': 'month_messages'}, inplace=True)
    plot_annotated_month_data(self_month_data, 'month', 'month_messages', 'title', annotate=False)

    # Self messages by month rolling average
    self_month_data['month_messages_roll_av'] = self_month_data.groupby('title')['month_messages'].transform(
        lambda x: x.rolling(3, 1).mean())
    plot_annotated_month_data(self_month_data, 'month', 'month_messages_roll_av', 'title', annotate=False)

    # Network plot
    network_df = create_network_df(messenger_data, slice=100)
    plot_network(network_df, seed=88, annotate=annotate_plots)

    # Network group plot
    network_group_df = create_network_df(messenger_data, slice=60, group=True)
    plot_network(network_group_df, seed=88, annotate=annotate_plots, group=True)
