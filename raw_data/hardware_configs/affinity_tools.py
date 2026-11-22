import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from scripts.cpu_affinity_map import get_cpu_topology


def get_topology_info():
    cores = get_cpu_topology()
    primary_ids = [c['logical_ids'][0] for c in cores]
    secondary_ids = [c['logical_ids'][1] for c in cores if len(c['logical_ids']) > 1]
    return primary_ids, secondary_ids

def get_dynamic_affinity_mask(num_physical_cores=12, exclude_os_cores=2):
    primary_ids, _ = get_topology_info()
    total_phys = len(primary_ids)

    if exclude_os_cores + num_physical_cores > total_phys:
        # adjust to fit
        exclude_os_cores = max(0, total_phys - num_physical_cores)

    selected_cores = primary_ids[exclude_os_cores : exclude_os_cores + num_physical_cores]
    mask = 0
    for tid in selected_cores:
        mask |= (1 << tid)

    return {
        "selected_logical_ids": selected_cores,
        "mask_int": mask,
        "mask_hex": hex(mask),
        "active_cores_count": len(selected_cores),
        "os_isolated_cores": primary_ids[:exclude_os_cores]
    }

if __name__ == '__main__':
    info_12 = get_dynamic_affinity_mask(num_physical_cores=12, exclude_os_cores=2)
    print("=== DYNAMIC AFFINITY (12 PHYSICAL CORES, 2 OS ISOLATED) ===")
    print("Selected Logical IDs:", info_12['selected_logical_ids'])
    print("OS Isolated IDs:     ", info_12['os_isolated_cores'])
    print("Mask Hex:            ", info_12['mask_hex'])
    print("Active Cores Count:  ", info_12['active_cores_count'])

    info_14 = get_dynamic_affinity_mask(num_physical_cores=14, exclude_os_cores=0)
    print("\n=== DYNAMIC AFFINITY (ALL 14 PHYSICAL CORES) ===")
    print("Mask Hex:            ", info_14['mask_hex'])
    print("Active Cores Count:  ", info_14['active_cores_count'])
