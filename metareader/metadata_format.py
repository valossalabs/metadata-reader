# -*- coding: utf-8 -*-
"""metadata_format.py"""

# The newer version has all fields in earlier versions
# TODO: Update to current version
metadata_versions = {
    "1.3.2": {
        "detections": {
            "ID": {
                "a": {
                    "similar_to": [{
                      # Is this correct:  "role": "..."
                    }]
                }
            }
        }
    },
    "1.3.1": {
        "version_info": {
            "metadata_type": "[core,???]"
        }
    },
    "1.3.0": {
        "version_info": {
            "metadata_format": "1.3.0",
            "backend": "",
        },
        "job_info": {
            "job_id": "",
            "request": {
                "media": {
                    "video": {
                        "url": ""
                    },
                    "transcript": {
                        "url": ""
                    },
                    "description": "[null,???]",
                    "language": "[en_US,???]",
                    "title": ""
                }
            }
        },
        "media_info": {
            "technical": {
                "duration_s": 1234.56789,       # Video length
                "fps": 24
            },
            "from_customer": {
                "title": ""
            }
        },
        "transcript": {},
        "detections": {
            "[1,2,...]": {
                "a": {                          # If "t" == "human.face"
                    "gender": {
                        "c": 0.123,             # Confidence
                        "value": "male/female"
                    },
                    "s_visible": 1.23,
                    "similar_to": [             # Optional
                        {
                            "c": 0.123,         # Confidence, 0.5-1.0
                            "name": "..."
                        }
                    ]
                },
                "cid": "Valossa Concept ID",    # Optional
                "ext_refs": {                   # Optional
                    "gkg": {                    # Google Knowledge Graph identifier
                        "id": "/m/xxxxx"
                    }
                },
                "label": "...",
                "occs": [
                    {
                        "c_max": 0.123,         # Maximum confidence of occurrence, not in human.face
                        "id": "[1,2,3,...]",    # Occurrence identifier
                        "ss": 12.34,            # Second, start
                        "se": 23.45             # Second, end
                    },
                    {},
                ],
                "t": "..."                      # Detection type
            },
        },
        "detection_groupings": {
            "by_detection_type": {              # Only types that has contents are included.
                "human.face_group": [],         # Each type has detections sorted by prominence.
                "visual.context": [],
                "audio.context": [],
                "...": []
            },
            "by_second": [                      # List containing all seconds in order
                [                               # Contains all occurrences in one second
                    {
                        "c": 0.123,             # optional?
                        "d": "dID",
                        "o": []
                    }
                ],
                []
            ]
        },
        "segmentations": {}
    }
}


def get_all_detections(metadata, det_type=None, n_most_prominent=float("inf")):
    """List all detections unless type or count is limited"""
    if not det_type:
        for detection_type in metadata["detection_groupings"]["by_detection_type"]:
            for detection_id, detection in get_all_detections(
                    metadata, det_type=detection_type, n_most_prominent=n_most_prominent
            ):
                yield detection_id, detection
    else:
        count = 0
        for detection_id in metadata["detection_groupings"]["by_detection_type"][det_type]:
            if count > n_most_prominent:
                break
            yield detection_id, metadata["detections"][detection_id]
            count += 1


def get_all_occs_by_second_data(metadata, start=0, stop=None, det_type=None):
    """yields every second of metadata unless limited"""
    if stop is None:
        # Make sure that stop is bigger than index
        stop = float('inf')
    index = start
    for second in metadata["detection_groupings"]["by_second"][start:]:
        if index > stop:
            break
        for secdata in second:
            if det_type and metadata["detections"][secdata["d"]]["t"] not in det_type:
                continue
            yield secdata


def get_subtitle_data(metadata, start=0, stop=None, det_type=None):
    """Yields data needed for subtitle generation

    Format: [start, stop, label/name]
    """
    for secdata in get_all_occs_by_second_data(metadata, start, stop, det_type):
        detection = metadata[u"detections"][secdata[u"d"]]
        # Get start and stop times for detection:
        for occ in detection[u"occs"]:  # Find the occ
            if occ[u"id"] == secdata[u"o"][0]:
                start = occ[u"ss"]
                stop = occ[u"se"]
        # Generate label:
        if "a" in detection:
            # human.face (most likely?)
            if "similar_to" in detection["a"]:
                label = detection["a"]["similar_to"][0]["name"]
            elif "gender" in detection["a"]:
                label = "unknown {}".format(detection["a"]["gender"]["value"])
            else:
                label = "unknown person"

        elif "label" in detection:
            label = detection["label"]
        else:
            raise RuntimeError("No 'a' or 'label' in detection")
        yield [start, stop, label]


def get_all_by_second_data(metadata, start=0, stop=None):
    """yields every second of metadata unless limited"""
    if stop is None:
        # Make sure that stop is bigger than index
        stop = float('inf')
    index = start
    for second in metadata["detection_groupings"]["by_second"][start:]:
        if index > stop:
            break
        yield second
        index += 1


def get_labels_by_second(metadata, start=0, stop=None, det_type=None, confidence=None):
    """Output just second with labels

    Format: [second, label,label,...]

    """
    if stop is None:
        stop = float('inf')
    index = start
    for second in metadata["detection_groupings"]["by_second"][start:]:
        if index > stop:
            break
        labels = [index]
        for occ in second:
            if det_type and metadata["detections"][occ["d"]]["t"] not in det_type:
                continue
            if confidence and occ["c"] < confidence:
                continue
            label = metadata["detections"][occ["d"]]["label"]
            labels.append(label)

        yield labels
        index += 1


class LengthSum(object):
    """Class to allow changing addition type.

    Union type addition simply extends time range when adding

    Normal type addition just adds end-start each time
    """
    def __init__(self, sum_type="normal"):
        self.compress_flag = False
        if sum_type == "union":
            self.add = self.add_union
            self.sum_type = "union"
            self.intervals = []
        elif sum_type == "normal":
            self.add = self.add_normal
            self.sum_type = "normal"
            self.sum = 0.0
        else:
            raise TypeError("sum_type must be either union or normal")

    def __str__(self):
        return str(self.__float__())

    def __repr__(self):
        return repr(self.__float__())

    def __float__(self):
        if self.compress_flag:
            self.intervals = self.compress(self.intervals)
        if self.sum_type == "union":
            r_sum = 0.0
            for interval in self.intervals:
                r_sum += interval[1] - interval[0]
            return r_sum
        return self.sum

    def __div__(self, other):
        return self.__float__() / other

    def add_union(self, ss, se):
        self.intervals.append((ss, se))
        self.compress_flag = True

    def add_normal(self, ss, se):
        self.sum += se - ss

    @staticmethod
    def compress(source_list):
        source_list.sort(key=lambda lis: lis[0])
        return_list = [source_list[0]]
        for cell in source_list[1:]:
            if cell[0] > return_list[-1][1]:
                return_list.append(cell)
            elif return_list[-1][1] <= cell[1]:
                return_list[-1] = (return_list[-1][0], cell[1])
        return return_list
