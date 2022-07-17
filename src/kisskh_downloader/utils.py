def get_matching_quality(
    expected_quality, available_qualities, select_closest_available
):
    resolutions = [quality.split("x") for quality in available_qualities]
    for resolution in resolutions:
        if expected_quality[:-1] in resolution[-1]:
            return "x".join(resolution)
    if select_closest_available:
        for resolution in resolutions:
            if expected_quality[:-1] <= resolution[-1]:
                return "x".join(resolution)
        else:
            return "x".join(resolution)
    for index, resolution in enumerate(resolutions, start=1):
        print(f"{index}. {'x'.join(resolution)}")
    choosen = int(input("Choose a quality: "))
    return "x".join(resolutions[choosen - 1])
