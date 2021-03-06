import os

from tvb_epilepsy.base.constants.config import Config
from tvb_epilepsy.base.constants.model_constants import K_DEF
from tvb_epilepsy.base.constants.model_inversion_constants import *
from tvb_epilepsy.base.utils.log_error_utils import warning
from tvb_epilepsy.base.utils.data_structures_utils import ensure_list, generate_region_labels
from tvb_epilepsy.base.model.timeseries import TimeseriesDimensions, Timeseries
from tvb_epilepsy.service.model_configuration_builder import ModelConfigurationBuilder
from tvb_epilepsy.service.lsa_service import LSAService
from tvb_epilepsy.io.h5_writer import H5Writer
from tvb_epilepsy.io.h5_reader import H5Reader
from tvb_epilepsy.top.scripts.hypothesis_scripts import from_hypothesis_to_model_config_lsa
from tvb_epilepsy.top.scripts.pse_scripts import pse_from_lsa_hypothesis
from tvb_epilepsy.top.scripts.simulation_scripts import from_model_configuration_to_simulation
from tvb_epilepsy.top.scripts.fitting_data_scripts import *


def set_model_config_LSA(head, hyp, reader, config, K_unscaled=K_DEF, tau1=TAU1_DEF, tau0=TAU0_DEF, pse_flag=True,
                         plotter=None, writer=None):
    model_configuration_builder = None
    lsa_service = None
    # --------------------------Model configuration and LSA-----------------------------------
    model_config_file = os.path.join(config.out.FOLDER_RES, hyp.name + "_ModelConfig.h5")
    hyp_file = os.path.join(config.out.FOLDER_RES, hyp.name + "_LSA.h5")
    if os.path.isfile(hyp_file) and os.path.isfile(model_config_file):
        # Read existing model configuration and LSA hypotheses...
        model_configuration = reader.read_model_configuration(model_config_file)
        lsa_hypothesis = reader.read_hypothesis(hyp_file)
    else:
        # ...or generate new ones
        model_configuration, lsa_hypothesis, model_configuration_builder, lsa_service = \
            from_hypothesis_to_model_config_lsa(hyp, head, eigen_vectors_number=None, weighted_eigenvector_sum=True,
                                                config=config, K=K_unscaled, tau1=tau1, tau0=tau0,
                                                save_flag=True, plot_flag=True)
        # --------------Parameter Search Exploration (PSE)-------------------------------
    if pse_flag:
        psa_lsa_file = os.path.join(config.out.FOLDER_RES, hyp.name + "_PSE_LSA_results.h5")
        try:
            pse_results = reader.read_dictionary(psa_lsa_file)
        except:
            logger.info("\n\nRunning PSE LSA...")
            n_samples = 100
            all_regions_indices = np.array(range(head.number_of_regions))
            disease_indices = lsa_hypothesis.regions_disease_indices
            healthy_indices = np.delete(all_regions_indices, disease_indices).tolist()
            if model_configuration_builder is None:
                model_configuration_builder = ModelConfigurationBuilder(hyp.number_of_regions, K=K_unscaled)
            if lsa_service is None:
                lsa_service =  LSAService(eigen_vectors_number=None, weighted_eigenvector_sum=True)
            pse_results = \
                pse_from_lsa_hypothesis(n_samples, lsa_hypothesis, head.connectivity.normalized_weights,
                                        model_configuration_builder, lsa_service, head.connectivity.region_labels,
                                        param_range=0.1, global_coupling=[{"indices": all_regions_indices}],
                                        healthy_regions_parameters=[ {"name": "x0_values", "indices": healthy_indices}],
                                        logger=logger, save_flag=False)[0]
            if plotter:
                plotter.plot_lsa(lsa_hypothesis, model_configuration, lsa_service.weighted_eigenvector_sum,
                                  lsa_service.eigen_vectors_number, head.connectivity.region_labels, pse_results)
            if writer:
                writer.write_dictionary(pse_results, psa_lsa_file)
    else:
        pse_results = {}
    return model_configuration, lsa_hypothesis, pse_results


def set_empirical_data(empirical_file, ts_file, head, sensors_lbls, sensor_id=0, seizure_length=SEIZURE_LENGTH,
                       times_on_off=[], label_strip_fun=None, plotter=None, title_prefix="", **kwargs):
    try:
        return H5Reader().read_timeseries(ts_file)
    except:
        # ... or preprocess empirical data for the first time:
        if len(sensors_lbls) == 0:
            sensors_lbls = head.get_sensors_id(sensor_ids=sensor_id).labels
        signals = prepare_seeg_observable_from_mne_file(empirical_file, head.get_sensors_id(sensor_ids=sensor_id),
                                                        sensors_lbls, seizure_length, times_on_off,
                                                        label_strip_fun=label_strip_fun, plotter=plotter,
                                                        title_prefix=title_prefix, **kwargs)
        H5Writer().write_timeseries(signals, ts_file)
        return signals


def set_simulated_target_data(ts_file, model_configuration, head, lsa_hypothesis, probabilistic_model, sensor_id=0,
                              sim_type="paper", times_on_off=[], config=Config(), plotter=None, title_prefix="",
                              **kwargs):
    if probabilistic_model.observation_model == OBSERVATION_MODELS.SEEG_LOGPOWER.value:
        seeg_gain_mode = "exp"
    else:
        seeg_gain_mode = "lin"
    signals, simulator = from_model_configuration_to_simulation(model_configuration, head, lsa_hypothesis,
                                                                sim_type=sim_type, ts_file=ts_file,
                                                                seeg_gain_mode=seeg_gain_mode,
                                                                config=config, plotter=plotter)
    try:
        probabilistic_model.ground_truth.update({"tau1": np.mean(simulator.model.tau1),
                                                 "tau0": np.mean(simulator.model.tau0),
                                                 "sigma": np.mean(simulator.simulation_settings.noise_intensity)})
    except:
        probabilistic_model.ground_truth.update({"tau1": np.mean(simulator.model.tt),
                                                 "tau0": 1.0 / np.mean(simulator.model.r),
                                                 "sigma": np.mean(simulator.simulation_settings.noise_intensity)})
    if probabilistic_model.observation_model in OBSERVATION_MODELS.SEEG.value:
        if probabilistic_model.observation_model != OBSERVATION_MODELS.SEEG_LOGPOWER.value:
            try:
                signals = signals["seeg"][sensor_id]
            except:
                signals = TimeseriesService().compute_seeg(signals["source"].get_source(),
                                                           head.get_sensors_id(sensor_ids=sensor_id))[0]
        else:
            signals = TimeseriesService().compute_seeg(signals["source"].get_source(),
                                                       head.get_sensors_id(sensor_ids=sensor_id), sum_mode="exp")[0]
        signals.data = -signals.data
        signals = prepare_seeg_observable(signals, probabilistic_model.time_length, times_on_off,
                                          plotter=plotter, title_prefix=title_prefix, **kwargs)

    else:
        signals = signals["source"].get_source()
        signals.data = -signals.data  # change sign to fit x1
        kwargs.pop("bipolar", None)
        signals = prepare_signal_observable(signals, probabilistic_model.time_length, times_on_off,
                                            plotter=plotter, title_prefix=title_prefix, **kwargs)
    return signals, simulator


def samples_to_timeseries(samples, model_data, target_data=None, regions_labels=[]):
    samples = ensure_list(samples)

    if isinstance(target_data, Timeseries):
        time = target_data.time_line
        n_target_data = target_data.number_of_labels
        target_data_labels = target_data.space_labels
    else:
        time = model_data.get("time", False)
        n_target_data = samples[0]["fit_target_data"]
        target_data_labels = generate_region_labels(n_target_data, [], ". ", False)

    if time is not False:
        time_start = time[0]
        time_step = np.diff(time).mean()
    else:
        time_start = 0
        time_step = 1

    if not isinstance(target_data, Timeseries):
        target_data = Timeseries(target_data,
                                 {TimeseriesDimensions.SPACE.value: target_data_labels,
                                  TimeseriesDimensions.VARIABLES.value: ["target_data"]},
                                  time_start=time_start, time_step=time_step)

    (n_times, n_regions, n_samples) = samples[0]["x1"].T.shape
    active_regions = model_data.get("active_regions", range(n_regions))
    regions_labels = generate_region_labels(np.maximum(n_regions, len(regions_labels)), regions_labels, ". ", False)
    if len(regions_labels) > len(active_regions):
        regions_labels = regions_labels[active_regions]

    for sample in ensure_list(samples):
        for x in ["x1", "z", "dX1t", "dZt"]:
            try:
                sample[x] = Timeseries(np.expand_dims(sample[x].T, 2), {TimeseriesDimensions.SPACE.value: regions_labels,
                                                     TimeseriesDimensions.VARIABLES.value: [x]},
                                       time_start=time_start, time_step=time_step, time_unit=target_data.time_unit)
            except:
                pass

        sample["fit_target_data"] = Timeseries(np.expand_dims(sample["fit_target_data"].T, 2),
                                               {TimeseriesDimensions.SPACE.value: target_data_labels,
                                                TimeseriesDimensions.VARIABLES.value: ["fit_target_data"]},
                               time_start=time_start, time_step=time_step)

    return samples, target_data
