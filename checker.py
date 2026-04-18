import re, sys

# ================= 映射与常数 =================
FLOOR_MAP = {
    **{f"B{i}": -i + 1 for i in range(1, 5)},
    **{f"F{i}": i for i in range(1, 8)}
}


def f_to_i(f):
    clean_f = f.strip()
    if clean_f not in FLOOR_MAP:
        print(f"DEBUG: 尝试解析非法楼层 -> '{clean_f}'")
        sys.exit(1)
    return FLOOR_MAP[clean_f]


class Checker:
    def __init__(self, infile):
        # elevs 存储电梯状态：f-楼层, open-门状态, ps-乘客, active-是否激活, status-模式
        self.elevs = {i: {"f": 1, "open": False, "ps": {}, "active": i <= 6, "status": "NORMAL"} for i in range(1, 13)}
        self.passengers = {}
        self.maint_workers = set()  # 专门记录检修工 ID
        self.cur_t = 0.0
        self.line_idx = 0

        # 预读输入文件
        try:
            with open(infile, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue

                    # 匹配普通乘客
                    p_normal = re.search(r"(\d+)-WEI-(\d+)-FROM-([^-]+)-TO-([^-]+)", line)
                    if p_normal:
                        pid = int(p_normal.group(1))
                        self.passengers[pid] = {
                            "to": f_to_i(p_normal.group(4)),
                            "w": int(p_normal.group(2)),
                            "done": False,
                            "in": False
                        }
                        continue

                    # 匹配检修指令 (检修工)
                    p_maint = re.search(r"MAINT-(\d+)-(\d+)-([^-]+)", line)
                    if p_maint:
                        # 格式说明：MAINT-电梯ID-工人ID-测试目标层
                        worker_id = int(p_maint.group(2))
                        self.maint_workers.add(worker_id)
                        self.passengers[worker_id] = {
                            "to": 1,  # 规则：检修工最终目的地固定为 F1
                            "test_floor": f_to_i(p_maint.group(3)),  # 记录测试层供后续扩展校验
                            "w": 1,
                            "done": False,
                            "in": False
                        }
        except FileNotFoundError:
            print(f"错误: 找不到输入文件 {infile}")
            sys.exit(1)

    def error(self, msg):
        print(f"\033[31m[WRONG]\033[0m 行 {self.line_idx}: {msg}")
        sys.exit(1)

    def check_collision(self, eid, current_floor):
        """物理冲突检查：同井道电梯不得同时出现在 F2"""
        if current_floor != 2: return
        sib_id = eid + 6 if eid <= 6 else eid - 6
        sib = self.elevs[sib_id]
        if sib["active"] and sib["f"] == 2:
            # 如果兄弟电梯也在 F2，无论是否开门，都是物理碰撞
            self.error(f"井道冲突：电梯 {eid} 与电梯 {sib_id} 同时位于 F2 层")

    def check(self, line):
        line = line.strip()
        if not line: return
        self.line_idx += 1
        m = re.match(r"\[\s*([\d\.]+)\]\s*(.*)", line)
        if not m: return
        t, content = float(m.group(1)), m.group(2)
        if t < self.cur_t - 0.001: self.error("时间戳倒流")
        self.cur_t = t

        parts = content.split("-")
        act = parts[0]
        try:
            eid = int(parts[-1])
        except ValueError:
            return

        e = self.elevs.get(eid)
        if not e: return

        if act == "ARRIVE":
            fl = f_to_i(parts[1])
            if e["open"]: self.error(f"电梯 {eid} 移动时未关门")
            if fl == 2: self.check_collision(eid, 2)

            # 边界检查
            if e["status"] == "DOUBLE":
                if eid <= 6 and fl < 2: self.error(f"主轿厢 {eid} 越界")
                if eid > 6 and fl > 2: self.error(f"备用轿厢 {eid} 越界")
            e["f"] = fl

        elif act == "OPEN":
            fl = f_to_i(parts[1])
            if fl == 2: self.check_collision(eid, 2)
            e["open"] = True

        elif act == "CLOSE":
            e["open"] = False

        elif act == "IN":
            pid = int(parts[1])
            if pid not in self.passengers or self.passengers[pid]["in"]:
                self.error(f"乘客 {pid} 状态异常（可能重复进入或不存在）")
            e["ps"][pid] = self.passengers[pid]["w"]
            self.passengers[pid]["in"] = True
            if sum(e["ps"].values()) > 400: self.error(f"电梯 {eid} 超重")

        elif act == "OUT":
            # 格式兼容：OUT-S-乘客ID-楼层-电梯ID 或 OUT-乘客ID-楼层-电梯ID
            pid = int(parts[2]) if parts[1] == "S" or parts[1] == "F" else int(parts[1])
            if pid not in e["ps"]: self.error(f"乘客 {pid} 不在电梯 {eid} 内")

            # 判定送达逻辑
            if pid in self.maint_workers:
                # 检修工：必须在 F1 下车
                if e["f"] == 1:
                    self.passengers[pid]["done"] = True
                else:
                    self.error(f"检修工 {pid} 必须回到 F1 才能下车，当前在 {parts[-2]}")
            else:
                # 普通乘客：必须到达目的地且标记为 S
                if parts[1] == "S" and e["f"] == self.passengers[pid]["to"]:
                    self.passengers[pid]["done"] = True

            del e["ps"][pid]
            self.passengers[pid]["in"] = False

        elif "UPDATE-BEGIN" in content:
            e["status"] = "UPDATING"
        elif "UPDATE-END" in content:
            e["status"] = "DOUBLE"
            self.elevs[eid + 6]["status"] = "DOUBLE"
            self.elevs[eid + 6]["active"] = True
            self.elevs[eid + 6]["f"] = 1
        elif "RECYCLE-BEGIN" in content:
            e["status"] = "RECYCLING"
        elif "RECYCLE-END" in content:
            e["active"] = False
            if eid > 6: self.elevs[eid - 6]["status"] = "NORMAL"

    def final(self):
        for pid, p in self.passengers.items():
            if not p["done"]:
                type_str = "检修工" if pid in self.maint_workers else "乘客"
                self.error(f"{type_str} {pid} 未送达目标楼层 (预期: {p['to']})")
        print("\033[32m[ACCEPTED]\033[0m")


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    c = Checker(sys.argv[1])
    for l in sys.stdin: c.check(l)
    c.final()