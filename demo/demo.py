"""
================================================================================
                    ANUGA GPU 最新 API 使用示例
================================================================================

本文件展示如何使用 ANUGA 最新的 GPU inlet 和 GPU 边界更新接口，
以及如何在手动时间步进中精确对齐 yield 和 finish 时刻。

核心概念：
1. GPU Inlet (最新方式): 
   - 初始化: domain.gpu_interface.init_gpu_inlets()
   - 添加: domain.gpu_inlets.add_inlet(region, Q=function, label=name, mode="cpu_compatible"|"fast")
   - 应用: domain.gpu_inlets.apply()

2. GPU 边界更新 (最新方式): 
   - 初始化: domain.gpu_interface.init_gpu_boundary_conditions()
   - 更新: domain.gpu_interface.update_boundary_values_gpu()

3. 时间步长对齐 (精确对齐到 checkpoint): 
   - 使用 TIME_EPS 浮点数容差进行时间检查
   - 动态缩放 dt 使其精确到达下一个 checkpoint 时刻
   - 若 dt 过小则直接跳到 checkpoint

================================================================================
"""

import math
from pathlib import Path

import anuga
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
CORE_GIT_BRANCH = "audit/sync-transfer-sw-domain-cuda"
CORE_GIT_COMMIT = "8134410"


"""
============================================================================
全局配置常数
============================================================================
"""

"""
运行时生成的演示网格文件路径
"""
GENERATED_MESH_DIR = SCRIPT_DIR / "generated_meshes"
MESH_FILE = GENERATED_MESH_DIR / "demo_mesh.msh"
DEMO_BOUNDARY_TAGS = {"bottom": [0], "right": [1], "top": [2], "left": [3]}
DEMO_BOUNDING_POLYGON = [
    [0.0, 0.0],
    [100.0, 0.0],
    [100.0, 50.0],
    [0.0, 50.0],
]
DEMO_MAXIMUM_TRIANGLE_AREA = 10.0

"""
TIME_EPS: 浮点数精度容差 (秒)
- 用于判断时间是否"足够接近"某个 checkpoint
- 在比较 relative_time 和 checkpoint 时使用
- 示例: if relative_time + TIME_EPS >= next_checkpoint_time
- 值越小越严格；1e-12 适合大多数工程应用
"""
TIME_EPS = 1.0e-12

"""
Inlet 位置和大小参数
"""
INLET1_CENTER = [10.0, 10.0]
INLET1_RADIUS = 20.0
INLET2_CENTER = [50.0, 20.0]
INLET2_RADIUS = 10.0


def q1(t: float) -> float:
    """
    第一个 inlet 的流量函数 Q(t) [单位: m³/s]
    恒定流量
    """
    return 10.0


def q2(t: float) -> float:
    """
    第二个 inlet 的流量函数 Q(t) [单位: m³/s]
    随时间变化的正弦周期流量
    周期约 6.28 秒
    """
    return 5.0 + 2.0 * math.sin(t)


def compute_gpu_domain_timestep(domain) -> float:
    dt = domain.gpu_interface.compute_fluxes_ext_central_kernel(
        domain.evolve_max_timestep,
        transfer_from_cpu=False,
        transfer_gpu_results=False,
        return_domain_timestep=True,
    )
    return float(np.asarray(dt).reshape(-1)[0])


def sync_gpu_update_timestep(domain) -> None:
    domain.gpu_interface.set_gpu_update_timestep(domain.timestep)


def ensure_demo_mesh(mesh_path: Path) -> None:
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    if mesh_path.exists():
        return

    domain = anuga.create_domain_from_regions(
        DEMO_BOUNDING_POLYGON,
        boundary_tags=DEMO_BOUNDARY_TAGS,
        maximum_triangle_area=DEMO_MAXIMUM_TRIANGLE_AREA,
        mesh_filename=str(mesh_path),
        minimum_triangle_angle=28.0,
        use_cache=False,
        verbose=False,
    )
    del domain


"""
============================================================================
演示 1: 最新 GPU Inlet API 使用
============================================================================

这个演示展示如何：
1) 初始化 GPU inlet 系统
2) 添加多个 inlet，支持不同的计算模式
3) 手动进行时间步进，保证精确对齐到 checkpoint
4) 在每个 checkpoint 检查和输出模拟结果
"""

print("\n" + "="*80)
print("演示 1: 最新 GPU Inlet API 使用")
print("="*80 + "\n")

"""
========== 步骤 1: 创建 domain 并初始化基础参数 ==========
"""
print("[1] 创建演示网格并加载 domain...")
ensure_demo_mesh(MESH_FILE)
domain = anuga.create_domain_from_file(str(MESH_FILE))
domain.set_name("gpu_inlet_demo")

"""
设置水深限制 - 防止数值不稳定
- minimum_storable_height: 写入文件时的最小水深
- minimum_allowed_height: 计算时的最小水深
"""
domain.set_minimum_storable_height(0.001)
domain.set_minimum_allowed_height(0.001)

"""
设置地形、摩擦系数和初始水位
- elevation: 地形高程，这里设为 -0.1 (整个域都在水下 0.1m)
- friction: Manning 摩擦系数，这里设为 0.03
- stage: 初始水位，这里设为 0.0
"""
domain.set_quantity("elevation", lambda x, y: -0.1)
domain.set_quantity("friction", 0.03, location="centroids")
domain.set_quantity("stage", 0.0, location="centroids")

"""
设置边界条件 - 默认为反射边界
反射边界条件将流量反射回域内
"""
br = anuga.Reflective_boundary(domain)
domain.set_boundary({"left": br, "right": br, "top": br, "bottom": br})

"""
启用 GPU 加速
- set_multiprocessor_mode(4) 指定使用 4 个 CPU 线程处理其他任务
- set_gpu_interface() 初始化 GPU 接口，使 domain 可以调用 GPU 内核
"""
print("[1] 启用 GPU 加速...")
domain.set_multiprocessor_mode(4)
domain.set_gpu_interface()

"""
========== 步骤 2: 初始化 GPU inlet 系统 ==========

这是使用 GPU inlet 的第一步，必须在添加任何 inlet 前调用。
此调用在 GPU 上分配必要的内存和数据结构用于 inlet 计算。
"""
print("[2] 初始化 GPU inlet 系统...")
domain.gpu_interface.init_gpu_inlets()

"""
========== 初始化 GPU 边界条件系统 ==========

即使这里使用反射边界（简单边界），也应该调用 init_gpu_boundary_conditions()
来启用新的 GPU 边界更新 API。

这个初始化在 GPU 上准备边界处理的数据结构，后续步骤中会调用
update_boundary_values_gpu() 来在 GPU 上执行边界条件更新。
"""
print("[2] 初始化 GPU 边界条件系统...")
domain.gpu_interface.init_gpu_boundary_conditions()

"""
========== 步骤 3: 定义 inlet 区域并添加 inlet ==========

Inlet 是向域内注入流量的区域。这里我们添加两个 inlet：
- inlet1: 圆形区域，中心 [10, 10]，半径 20
- inlet2: 圆形区域，中心 [50, 20]，半径 10

两个 inlet 使用不同的模式来展示 GPU 新 API 的灵活性。
"""
print("[3] 添加 inlet 区域...")

"""
创建第一个 inlet 区域
anuga.Region() 定义一个圆形子区域，用于指定 inlet 作用范围
"""
region1 = anuga.Region(
    domain=domain,
    center=INLET1_CENTER,  # 中心位置 [x, y]
    radius=INLET1_RADIUS   # 半径
)

"""
添加第一个 inlet 到系统
参数说明：
- region1: 作用区域
- Q=q1: 流量函数，参数为时间 t，返回值单位 m³/s
- label="inlet1": inlet 标识，用于日志和诊断
- mode="cpu_compatible": 计算模式（见下面的对比说明）
"""
domain.gpu_inlets.add_inlet(
    region1,
    Q=q1,
    label="inlet1",
    mode="cpu_compatible"
)

"""
创建第二个 inlet 区域
"""
region2 = anuga.Region(
    domain=domain,
    center=INLET2_CENTER,
    radius=INLET2_RADIUS
)

"""
添加第二个 inlet - 使用另一个模式进行对比

GPU inlet 模式对比说明：
1. "cpu_compatible" 模式:
   - 与标准 CPU inlet_operator 行为一致
   - 流量注入方式更加保守，接近 CPU 参考实现
   - 适合需要与 CPU 结果对齐或数值稳定性优先的场景
   
2. "fast" 模式:
   - GPU 优化计算方式，计算更快
   - 数值行为可能与 CPU 略有差异
   - 适合对速度要求高、允许小的数值差异的大规模模拟
"""
domain.gpu_inlets.add_inlet(
    region2,
    Q=q2,
    label="inlet2",
    mode="fast"  # 使用不同的计算模式
)

"""
========== 步骤 4: 设置模拟参数 ==========
"""
print("[4] 设置模拟参数...")

"""
检查点间隔 (秒)
- 模拟器每到达这个时间间隔就会输出一次结果
- 这里设为 30 秒，表示每 30 秒有一个 checkpoint
"""
yieldstep = 30.0

"""
总模拟时长 (秒)
- 整个模拟的持续时间
- 这里设为 600 秒（10 分钟）
"""
duration = 600.0

"""
========== 步骤 5: 手动时间步进循环 (关键部分：精确对齐) ==========

为什么需要手动时间步进而不是用 domain.evolve()?
- 需要精确控制 checkpoint 时刻，不能超过
- 需要获取 GPU 计算的中间结果用于诊断
- 需要与其他模型同步时间步长
- 需要在特定时刻检查和比较结果

这个循环展示的是最新 GPU API 的完整时间步进流程。
"""
print("[5] 开始时间步进循环...\n")

"""
初始化时间跟踪变量
- next_check_t: 下一个 checkpoint 时刻
  第一个 checkpoint 在 yieldstep 秒时，然后每隔 yieldstep 增加一个
"""
next_check_t = yieldstep

"""
主循环
每次循环执行一个完整的时间步长 dt，从时刻 t 推进到 t+dt
"""
while True:
    """
    ==================== 子步骤 5.1: 计算非守恒中间步 ====================
    
    这些步骤必须在 finish_step 前完成，它们用于：
    1) 稳定数值解（防止负水深）
    2) 计算需要用于通量计算的梯度信息
    3) 计算通量和建议的时间步长
    """

    """
    1. 防止负水深和极小值
    
    在浅水方程中，水深 h = stage - elevation 必须非负。
    GPU 上的计算可能因数值误差产生小的负值。
    这个内核检查并修正这些问题。
    
    参数说明：
    - transfer_gpu_results=False: 运算结果留在 GPU 上，不拉回 CPU
      （节省数据传输，因为后续步骤仍在 GPU 上）
    - transfer_from_cpu=False: 不从 CPU 转移数据到 GPU
      （数据已经在 GPU 上）
    """
    domain.gpu_interface.protect_against_infinitesimal_and_negative_heights_kernal(
        transfer_gpu_results=False,
        transfer_from_cpu=False
    )

    """
    2. 二阶边缘值外推
    
    浅水方程采用限制斜率的二阶有限体积法。
    此方法计算三角形边上的物理量值，用于通量计算。
    这里外推已有的梯度信息到边上。
    """
    domain.gpu_interface.extrapolate_second_order_edge_sw_kernel(
        transfer_gpu_results=False,
        transfer_from_cpu=False
    )

    """
    2.5 应用边界条件（使用最新的 GPU 边界更新 API）
    
    这是演示 1 中使用新 API 的关键步骤。
    直接在 GPU 上更新所有边界值，无需 CPU 往返。
    """
    domain.gpu_interface.update_boundary_values_gpu()

    """
    3. 计算通量并获得建议的时间步长
    
    compute_fluxes_ext_central_kernel 在每条边上计算物理通量，
    并基于 CFL (Courant-Friedrichs-Lewy) 条件给出建议的时间步长。
    
    CFL 条件确保数值稳定性：
    dt < h / (u + c)
    其中 h 是网格大小，u 是流速，c 是波速。
    
    这里使用最新调用方式：
    - 在 GPU 上完成 `min(timestep_array) * CFL` 计算
    - 只把最终可用的 `dt` 标量回传到 CPU
    - 后续 `update_conserved_quantities_kernal()` 默认消费同一个 GPU-side timestep
    """
    dt = compute_gpu_domain_timestep(domain)

    """
    4. 再次防止负水深
    通量计算后再检查一次，确保安全性。
    """
    domain.gpu_interface.protect_against_infinitesimal_and_negative_heights_kernal(
        transfer_gpu_results=False,
        transfer_from_cpu=False
    )

    """
    ==================== 子步骤 5.2: 精确对齐时间步长 ====================
    
    这是确保模拟精确到达 checkpoint 的关键步骤。
    
    问题：
    在一个时间步长循环中，GPU 给出的 flux_dt 可能很大。
    如果直接用这个 dt，会导致时间跳过 checkpoint，
    无法在 checkpoint 时刻输出结果（或输出时间对不上）。
    
    解决方案：
    动态调整 dt，使其精确到达下一个 checkpoint。
    """

    """
    最新 GPU 调用方式下，返回值 dt 已经是 GPU 上完成 CFL 处理后的时间步长，
    不需要再在 CPU 上执行 `flux_dt * domain.CFL`。
    """

    """
    确定下一个"事件"时刻
    事件可能是：
    - checkpoint: next_check_t (下一个要输出的时刻)
    - 结束: duration (最终模拟时刻)
    两者取较小值
    """
    next_event = min(next_check_t, duration)

    """
    计算从当前时刻到达下一个事件还需时间
    remaining = 下一个事件距离现在还有多少秒
    
    domain.relative_time: 记录 domain 从开始到现在已演化的总时间
    """
    remaining = next_event - domain.relative_time

    """
    ============ 核心对齐逻辑 ============
    
    如果建议的 dt 大于剩余时间，缩小 dt 使其精确到达 next_event：
    dt = min(dt, remaining)
    
    这保证了：
    domain.relative_time + dt == next_event (在浮点精度范围内)
    """
    dt = min(dt, remaining)

    """
    特殊处理极小的 dt：
    
    背景：浮点数比较总有误差。如果 dt 非常小（< TIME_EPS），
    说明已经非常接近 checkpoint 了，可能是由于符点舍入。
    
    处理方式：
    如果 dt <= TIME_EPS，直接用 remaining 作为最后一小步的 dt。
    这一步会让 domain.relative_time 精确到达 next_event。
    """
    if dt <= TIME_EPS:
        dt = max(remaining, 0.0)

    """
    ==================== 子步骤 5.3: 更新 domain 的时间参数 ====================
    
    告诉 domain 这个步长用的是什么值。
    domain 需要这些值来进行通量和方程求解。
    """

    """
    domain.timestep: 实际演化使用的时间步
    这是经过对齐调整后的、实际要推进的时间步长
    """
    domain.timestep = dt

    """
    如果 CPU 侧又对 dt 做了 checkpoint/finaltime 对齐调整，
    需要把这个最终 dt 明确同步回 GPU，确保 update kernel 使用同一数值。
    """
    sync_gpu_update_timestep(domain)

    """
    domain.relative_time: 当前已演化时间（累积）
    每个步长结束后，累加这个 dt
    这个值用于判断是否到达 checkpoint
    """
    domain.relative_time += dt

    """
    ==================== 子步骤 5.4: 完成时间步 - 应用物理方程 ====================
    
    这些步骤在 domain 时间推进一小步，即：
    stage_{n+1} = f(stage_n, ..., dt)
    的计算过程。
    """

    """
    计算 Manning 摩擦力强制项
    
    浅水方程中，摩擦力以源项出现：
    du/dt = ... - g * friction * u / h
    
    这个内核计算并添加这个源项的贡献。
    """
    domain.gpu_interface.compute_forcing_terms_manning_friction_flat(
        transfer_from_cpu=False,
        transfer_gpu_results=False
    )

    """
    ========== 应用 inlet 流量注入（最新 GPU inlet API）==========
    
    这是使用 gpu_inlets 的关键步骤！
    
    在这个时刻，根据 Q(t) 和 Q(t+dt/2) 等（具体取决于时间积分），
    向之前定义的 inlet 区域注入流量。
    
    注意：inlet 区域是在前面用 add_inlet() 定义的。
    这里只需要调用 apply()，系统自动处理所有 inlet 的流量注入。
    """
    domain.gpu_inlets.apply()

    """
    更新守恒量
    
    浅水方程三个守恒量：
    - stage (水面高程) h
    - xmomentum (x 方向动量) hu
    - ymomentum (y 方向动量) hv
    
    这个内核根据通量和源项更新这些量：
    U_{n+1} = U_n - dt * div(F) + dt * S
    
    其中 F 是通量，S 是源项（包括摩擦、inlet 等）。
    """
    domain.gpu_interface.update_conserved_quantities_kernal(
        transfer_from_cpu=False,
        transfer_gpu_results=False
    )

    """
    ==================== 子步骤 5.5: 检查是否到达 checkpoint ====================
    
    每经过一个 checkpoint 时刻，输出诊断信息。
    """

    """
    检查条件：relative_time + TIME_EPS >= next_check_t
    
    这里加上 TIME_EPS 的原因：由于浮点舍入，relative_time 可能略小于
    exactly next_check_t，但已经"足够接近"了。
    TIME_EPS 的存在让判断更加健壮。
    """
    if domain.relative_time + TIME_EPS >= next_check_t:
        """
        将 centroid 值从 GPU 转移到 CPU 以便读取
        这是必要的，因为 GPU 上的数据 CPU 无法直接访问
        """
        domain.gpu_interface.gpu_to_cpu_centroid_values()

        """
        提取当前状态量
        """
        q = domain.quantities
        stage = q["stage"].centroid_values.copy()
        height = q["height"].centroid_values.copy()

        """
        计算全局诊断量
        - avg_stage: 全网格平均水位
        - max_height: 全网格最大水深
        这些简单的统计量可以快速检查模拟是否合理
        """
        avg_stage = float(np.mean(stage))
        max_height = float(np.max(height))

        """
        输出诊断信息
        """
        print(
            f"[t={domain.relative_time:8.1f}s {next_check_t:8.1f}] "
            f"avg_stage={avg_stage:.6e} max_height={max_height:.6e}"
        )

        """
        更新下一个 checkpoint 时刻
        """
        next_check_t += yieldstep

    """
    ==================== 子步骤 5.6: 检查模拟是否完成 ====================
    """

    """
    如果已经到达持续时间的末尾，停止循环
    """
    if domain.relative_time + TIME_EPS >= duration:
        break

print(f"\n演示 1 完成：运行了 {domain.relative_time:.1f} 秒\n")


"""
============================================================================
演示 2: 最新 GPU 边界更新 API 使用
============================================================================

这个演示展示如何使用新的 GPU 边界更新 API：
1) 初始化 GPU 边界条件系统
2) 在时间步进中调用 GPU 内核执行边界更新（不需要 CPU 往返）
3) 与 inlet 一起使用

新 API 的优势：
- 避免 GPU-CPU 数据转移的开销
- 边界更新完全在 GPU 上执行，更高效
- 适合大规模模拟
"""

print("="*80)
print("演示 2: 最新 GPU 边界更新 API 使用")
print("="*80 + "\n")

"""
========== 步骤 1: 创建新 domain 并初始化 ==========
"""
print("[1] 创建 domain 并加载网格...")
ensure_demo_mesh(MESH_FILE)
domain2 = anuga.create_domain_from_file(str(MESH_FILE))
domain2.set_name("gpu_boundary_demo")

domain2.set_minimum_storable_height(0.001)
domain2.set_minimum_allowed_height(0.001)

domain2.set_quantity("elevation", lambda x, y: -0.1)
domain2.set_quantity("friction", 0.03, location="centroids")
domain2.set_quantity("stage", 0.0, location="centroids")

"""
设置时间相关的边界条件
anuga.Time_boundary() 表示边界处的物理量随时间变化

function 参数是一个 lambda 或函数，输入时间 t，输出：
[stage_value, xmomentum_value, ymomentum_value]

这里定义下边界的水位随时间正弦变化：
stage(t) = 0.3 + 0.15 * sin(2π*t/3600)
周期 3600 秒（1 小时），幅度 0.15 m
"""
time_boundary = anuga.Time_boundary(
    domain=domain2,
    function=lambda t: [
        0.3 + 0.15 * math.sin(2.0 * math.pi * t / 3600.0),
        0.0,
        0.0
    ]
)

"""
其他边界为反射边界
"""
br = anuga.Reflective_boundary(domain2)

"""
组合边界：左、右、上为反射；下为时间相关边界
"""
domain2.set_boundary({
    "left": br,
    "right": br,
    "top": br,
    "bottom": time_boundary
})

"""
启用 GPU
"""
print("[1] 启用 GPU 加速...")
domain2.set_multiprocessor_mode(4)
domain2.set_gpu_interface()

"""
========== 步骤 2: 初始化 GPU 边界条件系统 (新 API 的关键！) ==========

这个初始化必须在第一次调用 update_boundary_values_gpu() 前执行：
1) 在 GPU 上为边界值分配内存
2) 编译边界条件内核
3) 设置边界参数到 GPU

如果跳过这个初始化，调用 update_boundary_values_gpu() 会失败。

这正是"新 API"与"旧 API"的区别：
- 旧 API: gpu_to_cpu_boundary_values() → update_boundary() → transfer_boundary_values_to_gpu()
        (需要 CPU 参与，多次数据传输)
- 新 API: init_gpu_boundary_conditions() (一次性) → update_boundary_values_gpu() (循环中)
        (GPU 直接处理，无需 CPU，更快)
"""
print("[2] 初始化 GPU 边界条件系统...")
domain2.gpu_interface.init_gpu_boundary_conditions()

"""
同时初始化 inlet 系统（为了让水流动起来）
"""
print("[2] 初始化 GPU inlet 系统...")
domain2.gpu_interface.init_gpu_inlets()

"""
添加 inlet
"""
region1 = anuga.Region(domain=domain2, center=INLET1_CENTER, radius=INLET1_RADIUS)
region2 = anuga.Region(domain=domain2, center=INLET2_CENTER, radius=INLET2_RADIUS)
domain2.gpu_inlets.add_inlet(region1, Q=q1, label="inlet1", mode="cpu_compatible")
domain2.gpu_inlets.add_inlet(region2, Q=q2, label="inlet2", mode="fast")

"""
========== 步骤 3: 设置模拟参数 ==========
"""
print("[3] 设置模拟参数...")

"""
检查点间隔：600 秒
"""
yieldstep2 = 600.0

"""
总长度：3600 秒（1 小时）
"""
duration2 = 3600.0

"""
========== 步骤 4: 手动时间步进循环（新边界 API 演示）==========
"""
print("[4] 开始时间步进循环...\n")

next_check_t2 = yieldstep2

while True:
    """
    ========== 准备步骤（与演示 1 相同）==========
    """
    domain2.gpu_interface.protect_against_infinitesimal_and_negative_heights_kernal(
        transfer_gpu_results=False,
        transfer_from_cpu=False
    )

    domain2.gpu_interface.extrapolate_second_order_edge_sw_kernel(
        transfer_gpu_results=False,
        transfer_from_cpu=False
    )

    """
    ==================== 关键步骤：调用最新的 GPU 边界更新内核 ====================
    
    这是演示 2 的核心！
    
    ========== 旧方式 (已弃用 - 仅供参考) ==========
    
    旧方式需要 3 个步骤，涉及 GPU-CPU 往返：
    
    1. domain.gpu_interface.gpu_to_cpu_boundary_values()
       将边界值从 GPU 拉到 CPU
       
    2. domain.update_boundary()
       在 CPU 上执行边界条件更新
       通常调用 anuga 的标准 update_boundary() 函数
       
    3. domain.transfer_boundary_values_to_gpu()
       把更新后的边界值转回 GPU
    
    问题：
    - 需要 3 次函数调用
    - 需要 2 次数据传输（GPU→CPU→GPU）
    - CPU 必须参与计算
    - 数据传输成本高，尤其在大规模网格上
    
    ========== 新方式 (当前推荐) ==========
    
    新方式只需 1 个步骤，完全在 GPU 上执行：
    """

    """
    直接在 GPU 上计算并更新边界值
    
    这个内核做的事情等价于：
    1) 根据 domain.set_boundary() 里定义的边界条件
    2) 计算当前时刻 t 的边界值
    3) 在边界三角形上更新 stage, xmomentum, ymomentum
    
    所有计算都在 GPU 上进行，无需 CPU 干涉。
    
    优势：
    - 快速：避免 GPU-CPU 数据传输
    - 简洁：一行代码替代三行
    - 高效：GPU 并行计算边界值
    """
    domain2.gpu_interface.update_boundary_values_gpu()

    """
    ========== 继续其他计算步骤（与演示 1 相同）==========
    """
    dt = compute_gpu_domain_timestep(domain2)

    domain2.gpu_interface.protect_against_infinitesimal_and_negative_heights_kernal(
        transfer_gpu_results=False,
        transfer_from_cpu=False
    )

    """
    时间步长对齐（与演示 1 相同）
    """
    remaining = min(next_check_t2, duration2) - domain2.relative_time
    dt = min(dt, remaining)
    if dt <= TIME_EPS:
        dt = max(remaining, 0.0)

    domain2.timestep = dt
    sync_gpu_update_timestep(domain2)
    domain2.relative_time += dt

    """
    完成时间步（与演示 1 相同）
    """
    domain2.gpu_interface.compute_forcing_terms_manning_friction_flat(
        transfer_from_cpu=False,
        transfer_gpu_results=False
    )

    domain2.gpu_inlets.apply()

    domain2.gpu_interface.update_conserved_quantities_kernal(
        transfer_from_cpu=False,
        transfer_gpu_results=False
    )

    """
    检查 checkpoint
    """
    if domain2.relative_time + TIME_EPS >= next_check_t2:
        domain2.gpu_interface.gpu_to_cpu_centroid_values()
        q = domain2.quantities
        avg_stage = float(np.mean(q["stage"].centroid_values))
        print(f"[t={domain2.relative_time:8.1f}s {next_check_t2:8.1f}] avg_stage={avg_stage:.6e}")
        next_check_t2 += yieldstep2

    """
    检查完成
    """
    if domain2.relative_time + TIME_EPS >= duration2:
        break

print(f"\n演示 2 完成：运行了 {domain2.relative_time:.1f} 秒\n")

"""
============================================================================
总结
============================================================================

本文件演示了：

1. GPU Inlet API（最新）:
   ✓ 初始化: domain.gpu_interface.init_gpu_inlets()
   ✓ 添加: domain.gpu_inlets.add_inlet(..., mode="cpu_compatible"|"fast")
   ✓ 应用: domain.gpu_inlets.apply() 在时间步进中
   ✓ 支持多个 inlet，各自独立的流量函数

2. GPU 边界更新 API（最新）:
   ✓ 初始化一次: domain.gpu_interface.init_gpu_boundary_conditions()
   ✓ 每步调用: domain.gpu_interface.update_boundary_values_gpu()
   ✓ 无 CPU 往返，完全 GPU 执行

3. 精确时间步长对齐:
   ✓ 使用 TIME_EPS 进行浮点精度检查
   ✓ 动态调整 dt 使其到达 checkpoint
   ✓ 特殊处理极小时间步
   ✓ 确保 checkpoint 时刻精确对齐

关键代码片段总结：

--- GPU Inlet 的关键调用 ---
domain.gpu_interface.init_gpu_inlets()                    # 初始化
domain.gpu_inlets.add_inlet(region, Q=func, mode="...")   # 添加
domain.gpu_inlets.apply()                                 # 应用

--- GPU 边界更新的关键调用 ---
domain.gpu_interface.init_gpu_boundary_conditions()       # 初始化
domain.gpu_interface.update_boundary_values_gpu()         # 执行

--- GPU timestep 的关键调用 ---
dt = compute_gpu_domain_timestep(domain)
dt = min(dt, remaining)                                   # 不超过 checkpoint
if dt <= TIME_EPS: dt = max(remaining, 0.0)              # 处理极小值
domain.timestep = dt
sync_gpu_update_timestep(domain)
domain.relative_time += dt                                # 累计时间
if domain.relative_time + TIME_EPS >= checkpoint: ...     # 检查 checkpoint

对应 core 版本:
- branch: 运行时自动探测
- commit: 运行时自动探测

============================================================================
"""

print("="*80)
print("所有演示完成！")
print(f"Demo 对应 core 版本: {CORE_GIT_BRANCH} @ {CORE_GIT_COMMIT}")
print("="*80)
