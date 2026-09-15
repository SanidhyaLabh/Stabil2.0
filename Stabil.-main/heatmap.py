import numpy as np

def generate_heatmap(trajectory, ideal_path):

    heatmap = []

    for item in trajectory:
        # Trajectory items might be (x, y), (x, y, color) or (x, y, z, color)
        # We just need the first two elements
        point = item[:2] 
        dist = min(
            [np.linalg.norm(np.array(point)-np.array(p)) for p in ideal_path]
        )

        if dist < 10:
            heatmap.append(("green", point))
        elif dist < 25:
            heatmap.append(("yellow", point))
        else:
            heatmap.append(("red", point))

    return heatmap
