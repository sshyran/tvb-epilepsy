import os
import numpy
import h5py
from tvb_epilepsy.base.datatypes.dot_dicts import DictDot, OrderedDictDot
from tvb_epilepsy.base.utils.data_structures_utils import isequal_string
from tvb_epilepsy.base.model.disease_hypothesis import DiseaseHypothesis
from tvb_epilepsy.base.model.vep.connectivity import Connectivity, ConnectivityH5Field
from tvb_epilepsy.base.model.vep.head import Head
from tvb_epilepsy.base.model.vep.sensors import Sensors, SensorsH5Field
from tvb_epilepsy.base.model.vep.surface import Surface, SurfaceH5Field
from tvb_epilepsy.base.model.timeseries import Timeseries, TimeseriesDimensions
from tvb_epilepsy.base.model.parameter import Parameter
from tvb_epilepsy.base.simulation_settings import SimulationSettings
from tvb_epilepsy.service.model_inversion.probabilistic_models_builders import *
from tvb_epilepsy.io.h5_model import read_h5_model
from tvb_epilepsy.io.h5_writer import H5Writer
from tvb_epilepsy.service.probabilistic_parameter_builder import generate_probabilistic_parameter


H5_TYPE_ATTRIBUTE = H5Writer().H5_TYPE_ATTRIBUTE
H5_SUBTYPE_ATTRIBUTE = H5Writer().H5_SUBTYPE_ATTRIBUTE
H5_TYPES_ATTRUBUTES = [H5_TYPE_ATTRIBUTE, H5_SUBTYPE_ATTRIBUTE]


class H5Reader(object):
    logger = initialize_logger(__name__)

    connectivity_filename = "Connectivity.h5"
    cortical_surface_filename = "CorticalSurface.h5"
    region_mapping_filename = "RegionMapping.h5"
    volume_mapping_filename = "VolumeMapping.h5"
    structural_mri_filename = "StructuralMRI.h5"
    sensors_filename_prefix = "Sensors"
    sensors_filename_separator = "_"

    def read_connectivity(self, path):
        """
        :param path: Path towards a custom Connectivity H5 file
        :return: Connectivity object
        """
        self.logger.info("Starting to read a Connectivity from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        weights = h5_file['/' + ConnectivityH5Field.WEIGHTS][()]
        tract_lengths = h5_file['/' + ConnectivityH5Field.TRACTS][()]
        region_centres = h5_file['/' + ConnectivityH5Field.CENTERS][()]
        region_labels = h5_file['/' + ConnectivityH5Field.REGION_LABELS][()]
        orientations = h5_file['/' + ConnectivityH5Field.ORIENTATIONS][()]
        hemispheres = h5_file['/' + ConnectivityH5Field.HEMISPHERES][()]

        h5_file.close()

        conn = Connectivity(path, weights, tract_lengths, region_labels, region_centres, hemispheres, orientations)
        self.logger.info("Successfully read connectvity from: %s" % path)

        return conn

    def read_surface(self, path):
        """
        :param path: Path towards a custom Surface H5 file
        :return: Surface object
        """
        if not os.path.isfile(path):
            self.logger.warning("Surface file %s does not exist" % path)
            return None

        self.logger.info("Starting to read Surface from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        vertices = h5_file['/' + SurfaceH5Field.VERTICES][()]
        triangles = h5_file['/' + SurfaceH5Field.TRIANGLES][()]
        vertex_normals = h5_file['/' + SurfaceH5Field.VERTEX_NORMALS][()]

        h5_file.close()

        surface = Surface(vertices, triangles, vertex_normals)
        self.logger.info("Successfully read surface from: %s" % path)

        return surface

    def read_sensors(self, path):
        """
        :param path: Path towards a custom head folder
        :return: 3 lists with all sensors from Path by type
        """
        sensors_seeg = []
        sensors_eeg = []
        sensors_meg = []

        self.logger.info("Starting to read all Sensors from: %s" % path)

        all_head_files = os.listdir(path)
        for head_file in all_head_files:
            str_head_file = str(head_file)
            if not str_head_file.startswith(self.sensors_filename_prefix):
                continue

            type = str_head_file[len(self.sensors_filename_prefix):str_head_file.index(self.sensors_filename_separator)]
            if type.upper() == Sensors.TYPE_SEEG:
                sensors_seeg.append(self.read_sensors_of_type(os.path.join(path, head_file), Sensors.TYPE_SEEG))
            if type.upper() == Sensors.TYPE_EEG:
                sensors_eeg.append(self.read_sensors_of_type(os.path.join(path, head_file), Sensors.TYPE_EEG))
            if type.upper() == Sensors.TYPE_MEG:
                sensors_meg.append(self.read_sensors_of_type(os.path.join(path, head_file), Sensors.TYPE_MEG))

        self.logger.info("Successfuly read all sensors from: %s" % path)

        return sensors_seeg, sensors_eeg, sensors_meg

    def read_sensors_of_type(self, sensors_file, type):
        """
        :param
            sensors_file: Path towards a custom Sensors H5 file
            type: Senors type
        :return: Sensors object
        """
        if not os.path.exists(sensors_file):
            self.logger.warning("Senors file %s does not exist!" % sensors_file)
            return None

        self.logger.info("Starting to read sensors of type %s from: %s" % (type, sensors_file))
        h5_file = h5py.File(sensors_file, 'r', libver='latest')

        labels = h5_file['/' + SensorsH5Field.LABELS][()]
        locations = h5_file['/' + SensorsH5Field.LOCATIONS][()]

        if '/orientations' in h5_file:
            orientations = h5_file['/orientations'][()]
        else:
            orientations = None
        if '/' + SensorsH5Field.GAIN_MATRIX in h5_file:
            gain_matrix = h5_file['/' + SensorsH5Field.GAIN_MATRIX][()]
        else:
            gain_matrix = None

        h5_file.close()

        sensors = Sensors(labels, locations, orientations=orientations, gain_matrix=gain_matrix, s_type=type)
        self.logger.info("Successfully read sensors from: %s" % sensors_file)

        return sensors

    def read_volume_mapping(self, path):
        """
        :param path: Path towards a custom VolumeMapping H5 file
        :return: volume mapping in a numpy array
        """
        if not os.path.isfile(path):
            self.logger.warning("VolumeMapping file %s does not exist" % path)
            return numpy.array([])

        self.logger.info("Starting to read VolumeMapping from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        data = h5_file['/data'][()]

        h5_file.close()
        self.logger.info("Successfully read volume mapping!") #: %s" % data)

        return data

    def read_region_mapping(self, path):
        """
        :param path: Path towards a custom RegionMapping H5 file
        :return: region mapping in a numpy array
        """
        if not os.path.isfile(path):
            self.logger.warning("RegionMapping file %s does not exist" % path)
            return numpy.array([])

        self.logger.info("Starting to read RegionMapping from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        data = h5_file['/data'][()]

        h5_file.close()
        self.logger.info("Successfully read region mapping!") #: %s" % data)

        return data

    def read_t1(self, path):
        """
        :param path: Path towards a custom StructuralMRI H5 file
        :return: structural MRI in a numpy array
        """
        if not os.path.isfile(path):
            self.logger.warning("StructuralMRI file %s does not exist" % path)
            return numpy.array([])

        self.logger.info("Starting to read StructuralMRI from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        data = h5_file['/data'][()]

        h5_file.close()
        self.logger.info("Successfully read structural MRI from: %s" % path)

        return data

    def read_head(self, path):
        """
        :param path: Path towards a custom head folder
        :return: Head object
        """
        self.logger.info("Starting to read Head from: %s" % path)
        conn = self.read_connectivity(os.path.join(path, self.connectivity_filename))
        srf = self.read_surface(os.path.join(path, self.cortical_surface_filename))
        rm = self.read_region_mapping(os.path.join(path, self.region_mapping_filename))
        vm = self.read_volume_mapping(os.path.join(path, self.volume_mapping_filename))
        t1 = self.read_t1(os.path.join(path, self.structural_mri_filename))
        sensorsSEEG, sensorsEEG, sensorsMEG = self.read_sensors(path)

        head = Head(conn, srf, rm, vm, t1, path, sensorsSEEG=sensorsSEEG, sensorsEEG=sensorsEEG, sensorsMEG=sensorsMEG)
        self.logger.info("Successfully read Head from: %s" % path)

        return head

    def read_epileptogenicity(self, root_folder, name="ep"):
        """
        :param
            root_folder: Path towards a valid custom Epileptogenicity H5 file
            name: the name of the hypothesis
        :return: Timeseries in a numpy array
        """
        path = os.path.join(root_folder, name, name + ".h5")
        self.logger.info("Starting to read Epileptogenicity from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        values = h5_file['/values'][()]

        h5_file.close()
        self.logger.info("Successfully read epileptogenicity values!") #: %s" % values)

        return values

    def read_ts(self, path):
        """
        :param path: Path towards a valid TimeSeries H5 file
        :return: Timeseries data and time in 2 numpy arrays
        """
        self.logger.info("Starting to read TimeSeries from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        data = h5_file['/data'][()]
        total_time = int(h5_file["/"].attrs["Simulated_period"][0])
        nr_of_steps = int(h5_file["/data"].attrs["Number_of_steps"][0])
        start_time = float(h5_file["/data"].attrs["Start_time"][0])
        time = numpy.linspace(start_time, total_time, nr_of_steps)

        self.logger.info("First Channel sv sum: " + str(numpy.sum(data[:, 0])))
        self.logger.info("Successfully read timeseries!") #: %s" % data)
        h5_file.close()

        return time, data

    def read_timeseries(self, path):
        """
        :param path: Path towards a valid TimeSeries H5 file
        :return: Timeseries data and time in 2 numpy arrays
        """
        self.logger.info("Starting to read TimeSeries from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        data = h5_file['/data'][()]
        time = h5_file['/time'][()]
        labels = ensure_list(h5_file['/labels'][()])
        variables = ensure_list(h5_file['/variables'][()])
        time_unit = h5_file.attrs["time_unit"]
        self.logger.info("First Channel sv sum: " + str(numpy.sum(data[:, 0])))
        self.logger.info("Successfully read Timeseries!") #: %s" % data)
        h5_file.close()

        return Timeseries(data, {TimeseriesDimensions.SPACE.value: labels,
                                 TimeseriesDimensions.VARIABLES.value: variables},
                          time[0], np.mean(np.diff(time)), time_unit)

    def read_hypothesis(self, path, simplify=True):
        """
        :param path: Path towards a Hypothesis H5 file
        :return: DiseaseHypothesis object
        """
        self.logger.info("Starting to read Hypothesis from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        if h5_file.attrs["EPI_Subtype"] != "DiseaseHypothesis":
            self.logger.warning("This file does not seem to holds a DiseaseHypothesis!")

        hypothesis = DiseaseHypothesis()
        for dataset in h5_file.keys():
            hypothesis.set_attribute(dataset, h5_file["/" + dataset][()])

        for attr in h5_file.attrs.keys():
            if attr in ["x0_indices", "e_indices", "w_indices"]:
                hypothesis.set_attribute(attr, h5_file.attrs[attr].tolist())
            else:
                hypothesis.set_attribute(attr, h5_file.attrs[attr])

        h5_file.close()
        if simplify:
            hypothesis.simplify_hypothesis_from_h5()

        return hypothesis

    def read_model_configuration(self, path):
        """
        :param path: Path towards a ModelConfiguration H5 file
        :return: ModelConfiguration object
        """
        self.logger.info("Starting to read ModelConfiguration from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        if h5_file.attrs["EPI_Subtype"] != "ModelConfiguration":
            self.logger.warning("This file does not seem to hold a ModelConfiguration")

        model_configuration = ModelConfiguration()
        for dataset in h5_file.keys():
            model_configuration.set_attribute(dataset, h5_file["/" + dataset][()])

        for attr in h5_file.attrs.keys():
            model_configuration.set_attribute(attr, h5_file.attrs[attr])

        h5_file.close()
        return model_configuration

    def read_lsa_service(self, path):
        """
        :param path: Path towards a LSAService H5 file
        :return: LSAService object
        """
        self.logger.info("Starting to read LSAService from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')
        from tvb_epilepsy.service.lsa_service import LSAService
        lsa_service = LSAService()

        for dataset in h5_file.keys():
            lsa_service.set_attribute(dataset, h5_file["/" + dataset][()])

        for attr in h5_file.attrs.keys():
            lsa_service.set_attribute(attr, h5_file.attrs[attr])

        h5_file.close()
        return lsa_service

    def read_model_configuration_builder(self, path):
        """
        :param path: Path towards a ModelConfigurationService H5 file
        :return: ModelConfigurationService object
        """
        self.logger.info("Starting to read ModelConfigurationService from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        from tvb_epilepsy.service.model_configuration_builder import ModelConfigurationBuilder
        mc_service = ModelConfigurationBuilder()

        for dataset in h5_file.keys():
            mc_service.set_attribute(dataset, h5_file["/" + dataset][()])

        for attr in h5_file.attrs.keys():
            mc_service.set_attribute(attr, h5_file.attrs[attr])

        h5_file.close()
        return mc_service

    def read_model_inversion_service(self, path):
        """
                :param path: Path towards a ModelConfigurationService H5 file
                :return: ModelInversionService object
                """
        # TODO: add a specialized reader function
        model_inversion_service = self.read_dictionary(path, "OrderedDictDot")
        if model_inversion_service.dict.get("signals_inds", None) is not None:
            model_inversion_service.dict["signals_inds"] = model_inversion_service.dict["signals_inds"].tolist()
        return model_inversion_service

    def read_dictionary(self, path, type="dict"):
        """
        :param path: Path towards a dictionary H5 file
        :return: dict
        """
        self.logger.info("Starting to read a dictionary from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        dictionary = dict()
        for dataset in h5_file.keys():
            dictionary.update({dataset: h5_file["/" + dataset][()]})

        for attr in h5_file.attrs.keys():
            dictionary.update({attr: h5_file.attrs[attr]})

        h5_file.close()
        if isequal_string(type, "DictDot"):
            return DictDot(dictionary)
        elif isequal_string(type, "OrderedDictDot"):
            return OrderedDictDot(dictionary)
        else:
            return dictionary

    def read_simulation_settings(self, path):
        """
        :param path: Path towards a SimulationSettings H5 file
        :return: SimulationSettings
        """
        self.logger.info("Starting to read SimulationSettings from: %s" % path)
        h5_file = h5py.File(path, 'r', libver='latest')

        sim_settings = SimulationSettings()
        for dataset in h5_file.keys():
            sim_settings.set_attribute(dataset, h5_file["/" + dataset][()])

        for attr in h5_file.attrs.keys():
            sim_settings.set_attribute(attr, h5_file.attrs[attr])

        h5_file.close()
        return sim_settings

    def read_probabilistic_model(self, path):

        def strip_key_name(key):
            if key != "star":
                if key.find("_ProbabilityDistribution_") >= 0:
                    key_name = key.split("_ProbabilityDistribution_")[-1]
                elif key.find("_Parameter_") >= 0:
                    key_name = key.split("_Parameter_")[-1]
                else:
                    key_name = key
            return key_name

        def setattr_param(param, key, key_name, value):
            param.__setattr__(key_name, value)
            if key != key_name:
                try:
                    param.__setattr__(key, value)
                except:
                    pass

        def set_parameter_datasets(param, h5location):
            for key in h5location.keys():
                if key != "star":
                    key_name = strip_key_name(key)
                    if key.find("p_shape") >= 0:
                        setattr_param(param, key, key_name, tuple(h5location[key][()]))
                    else:
                        setattr_param(param, key, key_name, h5location[key][()])

        def set_parameter_attributes(param, h5location):
            for key in h5location.attrs.keys():
                if key not in H5_TYPES_ATTRUBUTES:
                    setattr_param(param, key, strip_key_name(key), h5location.attrs[key])

        h5_file = h5py.File(path, 'r', libver='latest')

        probabilistic_model = None
        epi_subtype = h5_file.attrs[H5_SUBTYPE_ATTRIBUTE]

        if H5_SUBTYPE_ATTRIBUTE == ProbabilisticModel.__name__:
            probabilistic_model = ProbabilisticModel()
        if epi_subtype == ODEProbabilisticModel.__name__:
            probabilistic_model = ODEProbabilisticModel()
        if epi_subtype == SDEProbabilisticModel.__name__:
            probabilistic_model = SDEProbabilisticModel()

        for attr in h5_file.attrs.keys():
            if attr not in H5_TYPES_ATTRUBUTES:
                probabilistic_model.__setattr__(attr, h5_file.attrs[attr])

        for key, value in h5_file.iteritems():
            if isinstance(value, h5py.Dataset):
                probabilistic_model.__setattr__(key, value[()])
            if isinstance(value, h5py.Group):
                if key == "model_config" and value.attrs[H5_SUBTYPE_ATTRIBUTE] == ModelConfiguration.__name__:
                    model_config = ModelConfiguration()

                    for mc_dataset in value.keys():
                        model_config.set_attribute(mc_dataset, value[mc_dataset][()])

                    for mc_attr in value.attrs.keys():
                        if mc_attr not in H5_TYPES_ATTRUBUTES:
                            model_config.__setattr__(mc_attr, value.attrs[mc_attr])

                    probabilistic_model.__setattr__(key, model_config)

                if key == "parameters":  # and value.attrs[epi_subtype_key] == OrderedDict.__name__:
                    parameters = OrderedDict()
                    for group_key, group_value in value.iteritems():
                        param_epi_subtype = group_value.attrs[H5_SUBTYPE_ATTRIBUTE]
                        if param_epi_subtype == "ProbabilisticParameter":
                            parameter = generate_probabilistic_parameter(
                                    probability_distribution=group_value.attrs["type"])
                        elif param_epi_subtype == "NegativeLognormal":
                            parameter = generate_negative_lognormal_parameter("", 1.0, 0.0, 2.0)
                            set_parameter_datasets(parameter.star, group_value["star"])
                            set_parameter_attributes(parameter.star, group_value["star"])
                        else:
                            parameter = Parameter()

                        set_parameter_datasets(parameter, group_value)
                        set_parameter_attributes(parameter, group_value)

                        parameters.update({group_key: parameter})

                    probabilistic_model.__setattr__(key, parameters)

                if key == "ground_truth":
                    for dataset in value.keys():
                        probabilistic_model.ground_truth[dataset] = value[dataset]
                    for attr in value.attrs.keys():
                        if attr not in H5_TYPES_ATTRUBUTES:
                            probabilistic_model.ground_truth[attr] = value.attrs[attr]

                if key == "active_regions":
                    probabilistic_model.active_regions = ensure_list(value)

        h5_file.close()
        return probabilistic_model

    def read_generic(self, path, obj=None, output_shape=None):
        return read_h5_model(path).convert_from_h5_model(obj, output_shape)
