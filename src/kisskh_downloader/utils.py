def get_matching_quality(expected_quality, available_qualities):
    for quality in available_qualities:
        if expected_quality[:-1] in quality:
            return quality
    else:
        return list(available_qualities)[-1]
