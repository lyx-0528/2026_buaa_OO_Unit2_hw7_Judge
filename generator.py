import random

# ================= 配置参数 =================
FLOORS = ["B4", "B3", "B2", "B1", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]
MAINT_TEST_FLOORS = ["B2", "B1", "F2", "F3"]
MAX_TOTAL_REQUESTS = 70
START_TIME = 1.1
FINAL_TIME_LIMIT = 50.0


class ElevatorState:
    def __init__(self, id):
        self.id = id
        self.status = "NORMAL"  # NORMAL, DOUBLE, INACTIVE
        self.last_op_end_time = 0.0
        self.has_updated = False
        self.has_recycled = False


class DataGenerator:
    def __init__(self):
        self.id_counter = 100
        self.all_requests = []
        self.elevators = {i: ElevatorState(i) for i in range(1, 13)}
        for i in range(7, 13):
            self.elevators[i].status = "INACTIVE"

    def add_passenger(self, time):
        if len(self.all_requests) >= MAX_TOTAL_REQUESTS: return
        p_id = self.id_counter
        self.id_counter += 1
        f_from, f_to = random.sample(FLOORS, 2)
        weight = random.randint(50, 100)
        self.all_requests.append([round(time, 1), f"[{time:.1f}]{p_id}-WEI-{weight}-FROM-{f_from}-TO-{f_to}"])

    def add_update(self, time):
        avail = [i for i, e in self.elevators.items() if i <= 6 and e.status == "NORMAL"
                 and not e.has_updated and time - e.last_op_end_time > 8.1]
        if not avail: return False
        e_id = random.choice(avail)
        self.elevators[e_id].status = "DOUBLE"
        self.elevators[e_id].has_updated = True
        self.elevators[e_id].last_op_end_time = time
        self.elevators[e_id + 6].status = "DOUBLE"
        self.elevators[e_id + 6].last_op_end_time = time
        self.all_requests.append([round(time, 1), f"[{time:.1f}]UPDATE-{e_id}"])
        return True

    def add_recycle(self, time):
        # 寻找目前处于 DOUBLE 状态的备用轿厢 (7-12)
        avail = [i for i, e in self.elevators.items() if i > 6 and e.status == "DOUBLE"
                 and time - e.last_op_end_time > 8.1]
        if not avail: return False
        e_id = random.choice(avail)
        self.elevators[e_id].status = "INACTIVE"
        self.elevators[e_id].has_recycled = True
        self.elevators[e_id].last_op_end_time = time
        self.elevators[e_id - 6].status = "NORMAL"
        self.elevators[e_id - 6].last_op_end_time = time
        self.all_requests.append([round(time, 1), f"[{time:.1f}]RECYCLE-{e_id}"])
        return True

    def add_maint(self, time):
        avail = [i for i, e in self.elevators.items() if i <= 6 and e.status == "NORMAL"
                 and time - e.last_op_end_time > 8.1]
        if not avail: return False
        e_id = random.choice(avail)
        w_id = self.id_counter
        self.id_counter += 1
        t_f = random.choice(MAINT_TEST_FLOORS)
        self.elevators[e_id].last_op_end_time = time
        self.all_requests.append([round(time, 1), f"[{time:.1f}]MAINT-{e_id}-{w_id}-{t_f}"])
        return True

    def generate(self):
        t = START_TIME
        # 阶段一：随机生成混合请求，直到接近指令上限或时间上限
        while len(self.all_requests) < MAX_TOTAL_REQUESTS - 12 and t < FINAL_TIME_LIMIT - 12:
            r = random.random()
            if r < 0.7:
                self.add_passenger(t)
                t += random.uniform(0.1, 0.4)
            elif r < 0.82:
                if self.add_update(t):
                    t += 0.2
                else:
                    t += 0.1
            elif r < 0.92:
                if self.add_maint(t):
                    t += 0.2
                else:
                    t += 0.1
            else:
                if self.add_recycle(t):
                    t += 0.2
                else:
                    t += 0.1

        # 阶段二：强制回收逻辑
        # 1. 找到所有还需要回收的备用轿厢
        to_recycle = [i for i, e in self.elevators.items() if i > 6 and e.status == "DOUBLE"]

        for eid in to_recycle:
            # 2. 检查 8s 间隔，如果不满足，直接把时间跳到满足为止
            needed_time = self.elevators[eid].last_op_end_time + 8.2
            if t < needed_time:
                t = needed_time

            # 3. 强制执行回收
            if self.add_recycle(t):
                t += 0.2

        # 排序并输出
        self.all_requests.sort(key=lambda x: x[0])
        for req in self.all_requests:
            print(req[1])


if __name__ == "__main__":
    DataGenerator().generate()