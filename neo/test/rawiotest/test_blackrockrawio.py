"""
Tests of neo.rawio.examplerawio
"""

import unittest

from neo.rawio.blackrockrawio import BlackrockRawIO
from neo.test.rawiotest.common_rawio_test import BaseTestRawIO

import numpy as np
from numpy.testing import assert_equal

try:
    import scipy.io

    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False


class TestBlackrockRawIO(
    BaseTestRawIO,
    unittest.TestCase,
):
    rawioclass = BlackrockRawIO
    entities_to_download = ["blackrock"]
    entities_to_test = [
        "blackrock/FileSpec2.3001",
        "blackrock/blackrock_2_1/l101210-001",
        "blackrock/blackrock_3_0/file_spec_3_0",
        "blackrock/blackrock_3_0_ptp/20231027-125608-001",
    ]

    @unittest.skipUnless(HAVE_SCIPY, "requires scipy")
    def test_compare_blackrockio_with_matlabloader(self):
        """
        This test compares the output of ReachGraspIO.read_block() with the
        output generated by a Matlab implementation of a Blackrock file reader
        provided by the company. The output for comparison is provided in a
        .mat file created by the script create_data_matlab_blackrock.m.
        The function tests LFPs, spike times, and digital events on channels
        80-83 and spike waveforms on channel 82, unit 1.
        For details on the file contents, refer to FileSpec2.3.txt

        Ported to the rawio API by Samuel Garcia.
        """

        # Load data from Matlab generated files
        ml = scipy.io.loadmat(self.get_local_path("blackrock/FileSpec2.3001.mat"))

        lfp_ml = ml["lfp"]  # (channel x time) LFP matrix
        ts_ml = ml["ts"]  # spike time stamps
        elec_ml = ml["el"]  # spike electrodes
        unit_ml = ml["un"]  # spike unit IDs
        wf_ml = ml["wf"]  # waveform unit 1 channel 1
        mts_ml = ml["mts"]  # marker time stamps
        mid_ml = ml["mid"]  # marker IDs

        # Load data in channels 1-3 from original data files using the Neo
        # BlackrockIO
        reader = BlackrockRawIO(filename=self.get_local_path("blackrock/FileSpec2.3001"))
        reader.parse_header()

        # Check if analog data on channels 1-8 are equal
        stream_index = 0
        self.assertGreater(reader.signal_channels_count(stream_index), 0)
        for c in range(0, 8):
            raw_sigs = reader.get_analogsignal_chunk(channel_indexes=[c], stream_index=stream_index)
            raw_sigs = raw_sigs.flatten()
            assert_equal(raw_sigs[:-1], lfp_ml[c, :])

        # Check if spikes in channels are equal
        nb_unit = reader.spike_channels_count()
        for spike_channel_index in range(nb_unit):
            unit_name = reader.header["spike_channels"][spike_channel_index]["name"]
            # name is chXX#YY where XX is channel_id and YY is unit_id
            channel_id, unit_id = unit_name.split("#")
            channel_id = int(channel_id.replace("ch", ""))
            unit_id = int(unit_id)

            matlab_spikes = ts_ml[(elec_ml == channel_id) & (unit_ml == unit_id)]

            io_spikes = reader.get_spike_timestamps(spike_channel_index=spike_channel_index)
            assert_equal(io_spikes, matlab_spikes)

            # Check waveforms of channel 1, unit 0
            if channel_id == 1 and unit_id == 0:
                io_waveforms = reader.get_spike_raw_waveforms(spike_channel_index=spike_channel_index)
                io_waveforms = io_waveforms[:, 0, :]  # remove dim 1
                assert_equal(io_waveforms, wf_ml)

        # Check if digital input port events are equal
        nb_ev_chan = reader.event_channels_count()
        # ~ print(reader.header['event_channels'])
        for ev_chan in range(nb_ev_chan):
            name = reader.header["event_channels"]["name"][ev_chan]
            # ~ print(name)
            all_timestamps, _, labels = reader.get_event_timestamps(event_channel_index=ev_chan)
            if name == "digital_input_port":
                for label in np.unique(labels):
                    python_digievents = all_timestamps[labels == label]
                    matlab_digievents = mts_ml[mid_ml == int(label)]
                    assert_equal(python_digievents, matlab_digievents)
            elif name == "comments":
                pass
                # TODO: Save comments to Matlab file.

    @unittest.skipUnless(HAVE_SCIPY, "requires scipy")
    def test_compare_blackrockio_with_matlabloader_v21(self):
        """
        This test compares the output of ReachGraspIO.read_block() with the
        output generated by a Matlab implementation of a Blackrock file reader
        provided by the company. The output for comparison is provided in a
        .mat file created by the script create_data_matlab_blackrock.m.
        The function tests LFPs, spike times, and digital events.

        Ported to the rawio API by Samuel Garcia.
        """

        dirname = self.get_local_path("blackrock/blackrock_2_1/l101210-001")
        # First run with parameters for ns5, then run with correct parameters for ns2
        parameters = [
            (
                "blackrock/blackrock_2_1/l101210-001_nev-02_ns5.mat",
                {"nsx_to_load": 5, "nev_override": "-".join([dirname, "02"])},
                96,
            ),
            ("blackrock/blackrock_2_1/l101210-001.mat", {"nsx_to_load": 2}, 6),
        ]
        for param in parameters:
            # Load data from Matlab generated files
            ml = scipy.io.loadmat(self.get_local_path(param[0]))
            lfp_ml = ml["lfp"]  # (channel x time) LFP matrix
            ts_ml = ml["ts"]  # spike time stamps
            elec_ml = ml["el"]  # spike electrodes
            unit_ml = ml["un"]  # spike unit IDs
            wf_ml = ml["wf"]  # waveforms
            mts_ml = ml["mts"]  # marker time stamps
            mid_ml = ml["mid"]  # marker IDs

            # Load data from original data files using the Neo BlackrockIO
            reader = BlackrockRawIO(dirname, **param[1])
            reader.parse_header()

            # Check if analog data are equal
            stream_index = 0
            self.assertGreater(reader.signal_channels_count(stream_index), 0)

            for c in range(0, param[2]):
                raw_sigs = reader.get_analogsignal_chunk(channel_indexes=[c])
                raw_sigs = raw_sigs.flatten()
                assert_equal(raw_sigs[:], lfp_ml[c, :])

            # Check if spikes in channels are equal
            nb_unit = reader.spike_channels_count()
            for spike_channel_index in range(nb_unit):
                unit_name = reader.header["spike_channels"][spike_channel_index]["name"]
                # name is chXX#YY where XX is channel_id and YY is unit_id
                channel_id, unit_id = unit_name.split("#")
                channel_id = int(channel_id.replace("ch", ""))
                unit_id = int(unit_id)

                matlab_spikes = ts_ml[(elec_ml == channel_id) & (unit_ml == unit_id)]

                io_spikes = reader.get_spike_timestamps(spike_channel_index=spike_channel_index)
                assert_equal(io_spikes, matlab_spikes)

                # Check all waveforms
                io_waveforms = reader.get_spike_raw_waveforms(spike_channel_index=spike_channel_index)
                io_waveforms = io_waveforms[:, 0, :]  # remove dim 1
                matlab_wf = wf_ml[np.nonzero(np.logical_and(elec_ml == channel_id, unit_ml == unit_id)), :][0]
                assert_equal(io_waveforms, matlab_wf)

            # Check if digital input port events are equal
            nb_ev_chan = reader.event_channels_count()
            # ~ print(reader.header['event_channels'])
            for ev_chan in range(nb_ev_chan):
                name = reader.header["event_channels"]["name"][ev_chan]
                # ~ print(name)
                if name == "digital_input_port":
                    all_timestamps, _, labels = reader.get_event_timestamps(event_channel_index=ev_chan)

                    for label in np.unique(labels):
                        python_digievents = all_timestamps[labels == label]
                        matlab_digievents = mts_ml[mid_ml == int(label)]
                        assert_equal(python_digievents, matlab_digievents)

    def test_blackrockrawio_ptp_timestamps(self):
        dirname = self.get_local_path("blackrock/blackrock_3_0_ptp/20231027-125608-001")
        reader = BlackrockRawIO(filename=dirname)
        reader.parse_header()

        # 1 segment; no pauses or detectable packet drops. Was ~2.1 seconds long
        self.assertEqual(1, reader.block_count())
        self.assertEqual(1, reader.segment_count(0))
        t_start = reader.segment_t_start(0, 0)
        t_stop = reader.segment_t_stop(0, 0)
        self.assertAlmostEqual(2.1, t_stop - t_start, places=1)

        # 2 streams - ns2 and ns6; each with 65 channels
        # 65 ns2 (1 kHz) channels, on the even channels -- every other from 2-130
        # 65 ns6 (RAW; 30 kHz) channels, on the odd channels -- every other from 1-129
        expected_rates = [1_000, 30_000]
        n_streams = reader.signal_streams_count()
        self.assertEqual(len(expected_rates), n_streams)
        for strm_ix in range(n_streams):
            reader.get_signal_sampling_rate(strm_ix)
            self.assertEqual(65, reader.signal_channels_count(strm_ix))
            self.assertAlmostEqual(expected_rates[strm_ix], reader.get_signal_sampling_rate(strm_ix), places=1)

        # Spikes enabled on channels 1-129 but channel 129 had 0 events.
        self.assertEqual(128, reader.spike_channels_count())


if __name__ == "__main__":
    unittest.main()
