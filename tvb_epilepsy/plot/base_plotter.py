# coding=utf-8

import os
import numpy
import matplotlib
from matplotlib import pyplot
from mpl_toolkits.axes_grid1 import make_axes_locatable
from tvb_epilepsy.base.constants.config import Config, FiguresConfig
from tvb_epilepsy.base.utils.log_error_utils import initialize_logger, warning
from tvb_epilepsy.base.utils.data_structures_utils import ensure_list


class BasePlotter(object):

    def __init__(self, config=None):
        self.config = config or Config()
        self.logger = initialize_logger(self.__class__.__name__, self.config.out.FOLDER_LOGS)

    def _check_show(self):
        if self.config.figures.SHOW_FLAG:
            # mp.use('TkAgg')
            pyplot.ion()
            pyplot.show()
        else:
            # mp.use('Agg')
            pyplot.ioff()
            pyplot.close()

    @staticmethod
    def _figure_filename(fig=None, figure_name=None):
        if fig is None:
            fig = pyplot.gcf()
        if figure_name is None:
            figure_name = fig.get_label()
        figure_name = figure_name.replace(": ", "_").replace(" ", "_").replace("\t", "_").replace(",", "")
        return figure_name

    def _save_figure(self, fig, figure_name):
        if self.config.figures.SAVE_FLAG:
            figure_name = self._figure_filename(fig, figure_name)
            figure_name = figure_name[:numpy.min([100, len(figure_name)])] + '.' + FiguresConfig.FIG_FORMAT
            figure_dir = self.config.out.FOLDER_FIGURES
            if not (os.path.isdir(figure_dir)):
                os.mkdir(figure_dir)
            pyplot.savefig(os.path.join(figure_dir, figure_name))

    @staticmethod
    def rect_subplot_shape(self, n, mode="col"):
        nj = int(numpy.ceil(numpy.sqrt(n)))
        ni = int(numpy.ceil(1.0 * n / nj))
        if mode.find("row") >= 0:
            return nj, ni
        else:
            return ni, nj

    @staticmethod
    def plot_vector(vector, labels, subplot, title, show_y_labels=True, indices_red=None, sharey=None):
        ax = pyplot.subplot(subplot, sharey=sharey)
        pyplot.title(title)
        n_vector = labels.shape[0]
        y_ticks = numpy.array(range(n_vector), dtype=numpy.int32)
        color = 'k'
        colors = numpy.repeat([color], n_vector)
        coldif = False
        if indices_red is not None:
            colors[indices_red] = 'r'
            coldif = True
        if len(vector.shape) == 1:
            ax.barh(y_ticks, vector, color=colors, align='center')
        else:
            ax.barh(y_ticks, vector[0, :], color=colors, align='center')
        # ax.invert_yaxis()
        ax.grid(True, color='grey')
        ax.set_yticks(y_ticks)
        if show_y_labels:
            region_labels = numpy.array(["%d. %s" % l for l in zip(range(n_vector), labels)])
            ax.set_yticklabels(region_labels)
            if coldif:
                labels = ax.yaxis.get_ticklabels()
                for ids in indices_red:
                    labels[ids].set_color('r')
                ax.yaxis.set_ticklabels(labels)
        else:
            ax.set_yticklabels([])
        ax.autoscale(tight=True)
        if sharey is None:
            ax.invert_yaxis()
        return ax

    @staticmethod
    def plot_vector_violin(dataset, vector=[], lines=[], labels=[], subplot=111, title="", violin_flag=True,
                           colormap="YlOrRd", show_y_labels=True, indices_red=None, sharey=None):
        ax = pyplot.subplot(subplot, sharey=sharey)
        # ax.hold(True)
        pyplot.title(title)
        n_violins = dataset.shape[1]
        y_ticks = numpy.array(range(n_violins), dtype=numpy.int32)
        # the vector plot
        coldif = False
        if indices_red is None:
            indices_red = []
        if violin_flag:
            # the violin plot
            colormap = matplotlib.cm.ScalarMappable(cmap=pyplot.set_cmap(colormap))
            colormap = colormap.to_rgba(numpy.mean(dataset, axis=0), alpha=0.75)
            violin_parts = ax.violinplot(dataset, y_ticks, vert=False, widths=0.9,
                                         showmeans=True, showmedians=True, showextrema=True)
            violin_parts['cmeans'].set_color("k")
            violin_parts['cmins'].set_color("b")
            violin_parts['cmaxes'].set_color("b")
            violin_parts['cbars'].set_color("b")
            violin_parts['cmedians'].set_color("b")
            for ii in range(len(violin_parts['bodies'])):
                violin_parts['bodies'][ii].set_color(numpy.reshape(colormap[ii], (1, 4)))
                violin_parts['bodies'][ii]._alpha = 0.75
                violin_parts['bodies'][ii]._edgecolors = numpy.reshape(colormap[ii], (1, 4))
                violin_parts['bodies'][ii]._facecolors = numpy.reshape(colormap[ii], (1, 4))
        else:
            colorcycle = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
            n_samples = dataset.shape[0]
            for ii in range(n_violins):
                for jj in range(n_samples):
                    ax.plot(dataset[jj, ii], y_ticks[ii], "D",
                            mfc=colorcycle[jj%n_samples], mec=colorcycle[jj%n_samples], ms=20)
        color = 'k'
        colors = numpy.repeat([color], n_violins)
        if indices_red is not None:
            colors[indices_red] = 'r'
            coldif = True
        if len(vector) == n_violins:
            for ii in range(n_violins):
                ax.plot(vector[ii], y_ticks[ii], '*', mfc=colors[ii], mec=colors[ii], ms=10)
        if len(lines) == 2 and lines[0].shape[0] == n_violins and lines[1].shape[0] == n_violins:
            for ii in range(n_violins):
                ax.plot(lines[0][ii],  y_ticks[ii] - 0.45*lines[1][ii]/numpy.max(lines[1][ii]), '--', color=colors[ii])
        ax.grid(True, color='grey')
        ax.set_yticks(y_ticks)
        if show_y_labels:
            region_labels = numpy.array(["%d. %s" % l for l in zip(range(n_violins), labels)])
            ax.set_yticklabels(region_labels)
            if coldif:
                labels = ax.yaxis.get_ticklabels()
                for ids in indices_red:
                    labels[ids].set_color('r')
                ax.yaxis.set_ticklabels(labels)
        else:
            ax.set_yticklabels([])
        if sharey is None:
            ax.invert_yaxis()
        ax.autoscale()
        return ax

    @staticmethod
    def plot_regions2regions(adj, labels, subplot, title, show_y_labels=True, show_x_labels=True,
                             indices_red_x=None, sharey=None):
        ax = pyplot.subplot(subplot, sharey=sharey)
        pyplot.title(title)
        y_color = 'k'
        adj_size = adj.shape[0]
        y_ticks = numpy.array(range(adj_size), dtype=numpy.int32)
        if indices_red_x is None:
            indices_red_x = y_ticks
            x_ticks = indices_red_x
            x_color = y_color
        else:
            x_color = 'r'
            x_ticks = range(len(indices_red_x))
        region_labels = numpy.array(["%d. %s" % l for l in zip(range(adj_size), labels)])
        cmap = pyplot.set_cmap('autumn_r')
        img = ax.imshow(adj[indices_red_x, :].T, cmap=cmap, interpolation='none')
        ax.set_xticks(x_ticks)
        ax.grid(True, color='grey')
        if show_y_labels:
            region_labels = numpy.array(["%d. %s" % l for l in zip(range(adj_size), labels)])
            ax.set_yticks(y_ticks)
            ax.set_yticklabels(region_labels)
            if not (x_color == y_color):
                labels = ax.yaxis.get_ticklabels()
                for idx in indices_red_x:
                    labels[idx].set_color('r')
                ax.yaxis.set_ticklabels(labels)
        else:
            ax.set_yticklabels([])
        if show_x_labels:
            ax.set_xticklabels(region_labels[indices_red_x], rotation=270, color=x_color)
        else:
            ax.set_xticklabels([])
        ax.autoscale(tight=True)
        # make a color bar
        divider = make_axes_locatable(ax)
        cax1 = divider.append_axes("right", size="5%", pad=0.05)
        pyplot.colorbar(img, cax=cax1)  # fraction=0.046, pad=0.04) #fraction=0.15, shrink=1.0
        return ax

    @staticmethod
    def _set_axis_labels(fig, sub, n_regions, region_labels, indices2emphasize, color='k', position='left'):
        y_ticks = range(n_regions)
        region_labels = numpy.array(["%d. %s" % l for l in zip(y_ticks, region_labels)])
        big_ax = fig.add_subplot(sub, frameon=False)
        if position == 'right':
            big_ax.yaxis.tick_right()
            big_ax.yaxis.set_label_position("right")
        big_ax.set_yticks(y_ticks)
        big_ax.set_yticklabels(region_labels, color='k')
        if not (color == 'k'):
            labels = big_ax.yaxis.get_ticklabels()
            for idx in indices2emphasize:
                labels[idx].set_color(color)
            big_ax.yaxis.set_ticklabels(labels)
        big_ax.invert_yaxis()
        big_ax.axes.get_xaxis().set_visible(False)
        # TODO: find out what is the next line about and why it fails...
        # big_ax.axes.set_facecolor('none')

    def plot_in_columns(self, data_dict_list, labels, width_ratios=[], left_ax_focus_indices=[],
                        right_ax_focus_indices=[], description="", title="", figure_name=None,
                        figsize=FiguresConfig.VERY_LARGE_SIZE, **kwargs):
        fig = pyplot.figure(title, frameon=False, figsize=figsize)
        fig.suptitle(description)
        n_subplots = len(data_dict_list)
        if not width_ratios:
            width_ratios = numpy.ones((n_subplots,)).tolist()
        matplotlib.gridspec.GridSpec(1, n_subplots, width_ratios=width_ratios)
        if 10 > n_subplots > 0:
            subplot_ind0 = 100 + 10 * n_subplots
        else:
            raise ValueError("\nSubplots' number " + str(n_subplots) + "is not between 1 and 9!")
        n_regions = len(labels)
        subplot_ind = subplot_ind0
        ax = None
        ax0 = None
        for iS, data_dict in enumerate(data_dict_list):
            subplot_ind += 1
            data = data_dict["data"]
            focus_indices = data_dict.get("focus_indices")
            if subplot_ind == 0:
                if not left_ax_focus_indices:
                    left_ax_focus_indices = focus_indices
            else:
                ax0 = ax
            if data_dict.get("plot_type") == "vector_violin":
                ax = self.plot_vector_violin(data_dict.get("data_samples", []), data, [],
                                             labels, subplot_ind, data_dict["name"],
                                             colormap=kwargs.get("colormap", "YlOrRd"), show_y_labels=False,
                                             indices_red=focus_indices, sharey=ax0)
            elif data_dict.get("plot_type") == "regions2regions":
                ax = self.plot_regions2regions(data, labels, subplot_ind, data_dict["name"], show_y_labels=False,
                                               show_x_labels=True, indices_red_x=focus_indices, sharey=ax0)
            else:
                ax = self.plot_vector(data, labels, subplot_ind, data_dict["name"], show_y_labels=False,
                                      indices_red=focus_indices, sharey=ax0)
        if right_ax_focus_indices == []:
            right_ax_focus_indices = focus_indices
        self._set_axis_labels(fig, 121, n_regions, labels, left_ax_focus_indices, 'r')
        self._set_axis_labels(fig, 122, n_regions, labels, right_ax_focus_indices, 'r', 'right')
        self._save_figure(pyplot.gcf(), figure_name)
        self._check_show()
        return fig

    def plots(self, data_dict, shape=None, transpose=False, skip=0, xlabels={}, xscales={}, yscales={}, title='Plots',
              figure_name=None, figsize=FiguresConfig.VERY_LARGE_SIZE):
        if shape is None:
            shape = (1, len(data_dict))
        fig, axes = pyplot.subplots(shape[0], shape[1], figsize=figsize)
        fig.set_label(title)
        for i, key in enumerate(data_dict.keys()):
            ind = numpy.unravel_index(i, shape)
            if transpose:
                axes[ind].plot(data_dict[key].T[skip:])
            else:
                axes[ind].plot(data_dict[key][skip:])
            axes[ind].set_xscale(xscales.get(key, "linear"))
            axes[ind].set_yscale(yscales.get(key, "linear"))
            axes[ind].set_xlabel(xlabels.get(key, ""))
            axes[ind].set_ylabel(key)
        fig.tight_layout()
        self._save_figure(fig, figure_name)
        self._check_show()
        return fig, axes

    def pair_plots(self, data, keys, diagonal_plots={}, transpose=False, skip=0,
                   title='Pair plots', legend_prefix="chains/runs", subtitles=None, figure_name=None,
                   figsize=FiguresConfig.VERY_LARGE_SIZE):

        def confirm_y_coordinate(data, ymax):
            data = list(data)
            data.append(ymax)
            return tuple(data)

        if subtitles is None:
            subtitles = keys
        data = ensure_list(data)
        n = len(keys)
        fig, axes = pyplot.subplots(n, n, figsize=figsize)
        fig.set_label(title)
        colorcycle = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
        for i, key_i in enumerate(keys):
            for j, key_j in enumerate(keys):
                for datai in data:
                    if transpose:
                        di = datai[key_i].T[skip:]
                    else:
                        di = datai[key_i][skip:]
                    if i == j:
                        if di.shape[0] > 1:
                            hist_data = axes[i, j].hist(di, int(numpy.round(numpy.sqrt(len(di)))), log=True)[0]
                            if i == 0 and len(di.shape) > 1 and di.shape[1] > 1:
                                axes[i, j].legend([legend_prefix + str(ii + 1) for ii in range(di.shape[1])])
                            y_max = numpy.array(hist_data).max()
                            # The mean line
                            axes[i, j].vlines(di.mean(axis=0), 0, y_max, color=colorcycle, linestyle='dashed',
                                              linewidth=1)
                        else:
                            # This is for the case of only 1 sample (optimization)
                            y_max = 1.0
                            for ii in range(di.shape[1]):
                                axes[i, j].plot(di[0, ii], y_max, "D", color=colorcycle[ii%di.shape[1]], markersize=20,
                                                label=legend_prefix + str(ii + 1))
                            if i == 0 and len(di.shape) > 1 and di.shape[1] > 1:
                                axes[i, j].legend()
                        # Plot a line (or marker) in the same axis
                        diag_line_plot = ensure_list(diagonal_plots.get(key_i, ((), ()))[0])
                        if len(diag_line_plot) in [1, 2]:
                            if len(diag_line_plot) == 1 :
                                diag_line_plot = confirm_y_coordinate(diag_line_plot, y_max)
                            else:
                                diag_line_plot[1] = diag_line_plot[1]/numpy.max(diag_line_plot[1])*y_max
                            if len(diag_line_plot[0]) == 1:
                                axes[i, j].plot(diag_line_plot[0], diag_line_plot[1], "o", mfc="k", mec="k",
                                                markersize=10)
                            else:
                                axes[i, j].plot(diag_line_plot[0], diag_line_plot[1], color='k',
                                                linestyle="dashed", linewidth=1)
                        # Plot a marker in the same axis
                        diag_marker_plot = ensure_list(diagonal_plots.get(key_i, ((), ()))[1])
                        if len(diag_marker_plot) in [1, 2]:
                            if len(diag_marker_plot) == 1:
                                diag_marker_plot = confirm_y_coordinate(diag_marker_plot, y_max)
                            axes[i, j].plot(diag_marker_plot[0], diag_marker_plot[1], "*", color='k', markersize=10)
                        axes[i, j].autoscale()
                        axes[i, j].set_ylim([0, 1.1*y_max])

                    else:
                        if transpose:
                            dj = datai[key_j].T[skip:]
                        else:
                            dj = datai[key_j][skip:]
                        axes[i, j].plot(dj, di, '.')
                if i == 0:
                    axes[i, j].set_title(subtitles[j])
                if j == 0:
                    axes[i, j].set_ylabel(key_i)
        fig.tight_layout()
        self._save_figure(fig, figure_name)
        self._check_show()
        return fig, axes

    def plot_bars(self, data, ax=None, fig=None, title="", group_names=[], legend_prefix="",
                  figsize=FiguresConfig.VERY_LARGE_SIZE):

        def barlabel(ax, rects, positions):
            """
            Attach a text label on each bar displaying its height
            """
            for rect, pos in zip(rects, positions):
                height = rect.get_height()
                if pos < 0:
                    y = -height
                    pos = 0.75 * pos
                else:
                    y = height
                    pos = 0.25 * pos
                ax.text(rect.get_x() + rect.get_width() / 2., pos, '%0.2f' % y,
                        color="k", ha='center', va='bottom', rotation=90)

        if fig is None:
            fig, ax = pyplot.subplots(1, 1, figsize=figsize)
            show_and_save = True
        else:
            show_and_save = False
            if ax is None:
                ax = pyplot.gca()
        if isinstance(data, (list, tuple)):  # If, there are many groups, data is a list:
            # Fill in with nan in case that not all groups have the same number of elements
            from itertools import izip_longest
            data = numpy.array(list(izip_longest(*ensure_list(data), fillvalue=numpy.nan))).T
        elif data.ndim == 1: # This is the case where there is only one group...
            data = numpy.expand_dims(data, axis=1).T
        n_groups, n_elements = data.shape
        posmax = data.max()
        negmax = -(-data).max()
        n_groups_names = len(group_names)
        if n_groups_names != n_groups:
            if n_groups_names != 0:
                warning("Ignoring group_names because their number (" + str(n_groups_names) +
                        ") is not equal to the number of groups (" + str(n_groups) + ")!")
            group_names = n_groups * [""]
        colorcycle = pyplot.rcParams['axes.prop_cycle'].by_key()['color']
        n_colors = len(colorcycle)
        x_inds = numpy.arange(n_groups)
        width = 0.9 / n_elements
        elements = []
        for iE in range(n_elements):
            elements.append(ax.bar(x_inds + iE*width, data[:, iE], width, color=colorcycle[iE % n_colors]))
            positions = [negmax if d < 0 else posmax for d in data[:, iE]]
            barlabel(ax, elements[-1], positions)
        if n_elements > 1:
            legend = [legend_prefix+str(ii) for ii in range(1, n_elements+1)]
            ax.legend(tuple([element[0] for element in elements]), tuple(legend))
        ax.set_xticks(x_inds + n_elements*width/2)
        ax.set_xticklabels(tuple(group_names))
        ax.set_title(title)
        ax.autoscale()  # tight=True
        ax.set_xlim([-1.05*width, n_groups*1.05])
        if show_and_save:
            fig.tight_layout()
            self._save_figure(fig)
            self._check_show()
        return fig, ax
