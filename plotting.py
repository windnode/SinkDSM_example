#!/usr/bin/env python
# coding: utf-8

# In[ ]:

from oemof import outputlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

import os
import pandas as pd
from pandas.plotting import register_matplotlib_converters

# register matplotlib converters which have been overwritten by pandas
register_matplotlib_converters()


#################################################################

def make_directory(folder_name):

    existing_folders = next(os.walk('.'))[1]
    if folder_name in existing_folders:
        print('----------------------------------------------------------')
        print('Folder "' + folder_name + '" already exists in current directory.')
        print('----------------------------------------------------------')
    else:
        path = "./" + folder_name
        os.mkdir(path)
        print('----------------------------------------------------------')
        print('Created folder "' + folder_name + '" in current directory.')
        print('----------------------------------------------------------')

def adjust_yaxis(ax, ydif, v):
    """shift axis ax by ydiff, maintaining point v at the same location"""
    inv = ax.transData.inverted()
    _, dy = inv.transform((0, 0)) - inv.transform((0, ydif))
    miny, maxy = ax.get_ylim()
    miny, maxy = miny - v, maxy - v
    if -miny > maxy or (-miny == maxy and dy > 0):
        nminy = miny
        nmaxy = miny * (maxy + dy) / (miny + dy)
    else:
        nmaxy = maxy
        nminy = maxy * (miny + dy) / (maxy + dy)
    ax.set_ylim(nminy + v, nmaxy + v)


def align_yaxis(ax1, v1, ax2, v2):
    """adjust ax2 ylimit so that v2 in ax2 is aligned to v1 in ax1"""
    _, y1 = ax1.transData.transform((0, v1))
    _, y2 = ax2.transData.transform((0, v2))
    adjust_yaxis(ax2, (y1 - y2) / 2, v2)
    adjust_yaxis(ax1, (y2 - y1) / 2, v1)


def extract_results(model):
    '''Extract data fro Pyomo Variables in DataFrames and plot for visualization'''

    # ########################### Get DataFrame out of Pyomo and rename series

    # Generators coal
    df_coal_1 = outputlib.views.node(model.es.results['main'], 'bus_elec')['sequences'][
        (('pp_coal_1', 'bus_elec'), 'flow')]
    df_coal_1.rename('coal1', inplace=True)


    # Generators RE
    df_wind = outputlib.views.node(model.es.results['main'], 'bus_elec')['sequences'][
        (('wind', 'bus_elec'), 'flow')]
    df_wind.rename('wind', inplace=True)

    df_pv = outputlib.views.node(model.es.results['main'], 'bus_elec')['sequences'][
        (('pv', 'bus_elec'), 'flow')]
    df_pv.rename('pv', inplace=True)

    # Shortage/Excess
    df_shortage = outputlib.views.node(model.es.results['main'], 'bus_elec')['sequences'][
        (('shortage_el', 'bus_elec'), 'flow')]
    df_shortage.rename('shortage', inplace=True)

    df_excess = outputlib.views.node(model.es.results['main'], 'bus_elec')['sequences'][
        (('bus_elec', 'excess_el'), 'flow')]
    df_excess.rename('excess', inplace=True)

    # DSM Demand
    df_demand_dsm = outputlib.views.node(model.es.results['main'], 'bus_elec')['sequences'][
        (('bus_elec', 'demand_dsm'), 'flow')]
    df_demand_dsm.rename('demand_dsm', inplace=True)

    # DSM Variables
    df_dsmdo = outputlib.views.node(model.es.results['main'], 'demand_dsm')['sequences'].iloc[:, 1:-1].sum(axis=1)
    df_dsmdo.rename('dsm_do', inplace=True)

    df_dsmup = outputlib.views.node(model.es.results['main'], 'demand_dsm')['sequences'].iloc[:, -1]
    df_dsmup.rename('dsm_up', inplace=True)

    df_dsm_tot = df_dsmdo - df_dsmup
    df_dsm_tot.rename('dsm_tot', inplace=True)

    df_dsm_acum = df_dsm_tot.cumsum()
    df_dsm_acum.rename('dsm_acum', inplace=True)


    # Demand
    df_demand_el = [_ for _ in model.NODES.value if str(_) == 'demand_dsm'][0].demand
    df_demand_el.rename('demand_el', inplace=True)

    # Demand
    df_capup = [_ for _ in model.NODES.value if str(_) == 'demand_dsm'][0].capacity_up
    df_capup.rename('cap_up', inplace=True)

    # Demand
    df_capdo = [_ for _ in model.NODES.value if str(_) == 'demand_dsm'][0].capacity_down
    df_capdo.rename('cap_do', inplace=True)

    ######## Merge in one DataFrame
    df_model = pd.concat([df_coal_1,  df_wind, df_pv, df_excess, df_shortage,
                           df_demand_dsm, df_dsmdo, df_dsmup, df_dsm_tot,
                           df_dsm_acum, df_demand_el, df_capup, df_capdo],
                          axis=1)

    return df_model


def plot_dsm(df_gesamt, datetimeindex, directory, timesteps, project, days, **kwargs):

    save = kwargs.get('save', False)

    # ############ DATA PREPARATION FOR FIGURE #############################

    # create Figure
    for info, slice in df_gesamt.resample(str(days)+'D'):
        
        # Generators from model
        # hierarchy for plot: wind, pv, coal, shortage
        graph_wind = slice.wind.values
        graph_pv = graph_wind + slice.pv.values
        graph_coal = graph_pv + slice.coal1.values
        graph_shortage = graph_coal + slice.shortage.values

        #################
        # first axis
        #get_ipython().run_line_magic('matplotlib', 'notebook')
        fig, ax1 = plt.subplots(figsize=(10, 10))
        ax1.set_ylim([-10, 250])

        # x-Axis date format
        ax1.xaxis_date()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m - %H h'))  # ('%d.%m-%H h'))
        ax1.set_xlim(info - pd.Timedelta(1, 'h'), info + pd.Timedelta(days*24+1, 'h'))
        plt.xticks(pd.date_range(start=info._date_repr, periods=days*24, freq='H'), rotation=90)

        # Demands
        # ax1.plot(range(timesteps), dsm, label='demand_DSM', color='black')
        ax1.step(slice.index, slice.demand_el.values, where='post', label='Demand', linestyle='--', color='blue')
        ax1.step(slice.index, slice.demand_dsm.values, where='post', label='Demand after DSM', color='black')

        # DSM Capacity
        ax1.plot(slice.index, slice.demand_el + slice.cap_up, label='DSM Capacity', color='red', linestyle='--')
        ax1.plot(slice.index, slice.demand_el - slice.cap_do, color='red', linestyle='--')

        # Generators
        ax1.fill_between(slice.index, 0, graph_wind, step='post', label='Wind', facecolor='darkcyan', alpha=0.5)
        ax1.fill_between(slice.index, graph_wind, graph_pv, step='post', label='PV', facecolor='gold', alpha=0.5)
        ax1.fill_between(slice.index, graph_pv, graph_coal, step='post', label='Coal', facecolor='black', alpha=0.5)
        ax1.fill_between(slice.index, slice.demand_dsm.values, graph_coal,
                         step='post',
                         label='Excess',
                         facecolor='firebrick',
                         hatch='/',
                         alpha=0.5)

        ax1.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=4, mode="expand", borderaxespad=0.)

        # plt.xticks(range(0,timesteps,5))

        plt.grid()


        ###########################
        # Second axis
        ax2 = ax1.twinx()
        ax2.xaxis_date()
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m - %H h'))  # ('%d.%m-%H h'))
        ax2.set_xlim(info - pd.Timedelta(1, 'h'), info + pd.Timedelta(days*24+1, 'h'))
        plt.xticks(pd.date_range(start=info._date_repr, periods=days*24, freq='H'), rotation=90)

        ax2.set_ylim([-110, 150])
        align_yaxis(ax1, 100, ax2, 0)


        # DSM up/down

        #ax2.step(slice.index, slice.dsm_acum, where='post',
        #         label='DSM acum', alpha=0.5, color='orange')

        ax2.fill_between(slice.index, 0, -slice.dsm_do,
                         step='post',
                         label='DSM_down',
                         facecolor='red',
                         #hatch='.',
                         alpha=0.3)
        ax2.fill_between(slice.index, 0, slice.dsm_up,
                         step='post',
                         label='DSM_down',
                         facecolor='green',
                         #hatch='.',
                         alpha=0.3)
        ax2.fill_between(slice.index, 0, slice.dsm_acum,
                         step='post',
                         label='DSM acum',
                         facecolor=None,
                         hatch='x',
                         alpha=0.0)

        # Legend axis 2
        ax2.legend(bbox_to_anchor=(0., -0.2, 1., 0.102), loc=3, ncol=3, borderaxespad=0., mode="expand")
        ax1.set_xlabel('Time t in h')
        ax1.set_ylabel('MW')
        ax2.set_ylabel('MW')



        if save:
            fig.set_tight_layout(True)
            name = 'Plot_' + project + '_' + info._date_repr + '.png'
            fig.savefig(directory + 'graphics/' + name)
            plt.close()
            print(name + ' saved.')

