import os
import json
import base64
import zstandard as zstd
from dataclasses import asdict

class WorldLog:
    def __init__(self, grid_array, log_dir="logs", flush_interval=100):
        self.grid_array = grid_array
        self.turn_count = 0
        self.flush_interval = flush_interval

        self.log_dir = log_dir
        self.raw_log_file = os.path.join(self.log_dir, "turn_logs.jsonl")
        self.static_file = os.path.join(self.log_dir, "static_data.jsonl")  # .jsonl로 변경
        self.compressed_dir = os.path.join(self.log_dir, "compressed")
        os.makedirs(self.compressed_dir, exist_ok=True)

        open(self.raw_log_file, "w").close()
        open(self.static_file, "w").close()

        self.static_creature_data = []
        self.compress_count = 0

    def register_creature(self, creatures):
        """새로운 생물체의 유전자 정보를 누적"""
        self.static_creature_data.extend([
            base64.b64encode(creature.genome.genome_bytes).decode('utf-8')
            for creature in creatures
        ])

    def write_static_data(self):
        """누적된 유전자 정보를 파일에 append한 뒤 리스트 초기화"""
        if self.static_creature_data:
            with open(self.static_file, "a", encoding="utf-8") as f:
                for genome_str in self.static_creature_data:
                    f.write(json.dumps(genome_str) + "\n")
            self.static_creature_data.clear()

    def log_turn(self):
        """매 턴마다 로그를 기록"""
        turn_log = {
            "turn": self.turn_count,
            "grids": [[{
                "pos": asdict(grid.pos),
                "organics": grid.organics.current_amounts,
                "creatures": [{
                    "id": creature.id,
                    "position": asdict(creature.position),
                    "health": creature.health,
                    "energy": creature.energy
                } for creature in grid.creatures]
            } for grid in row] for row in self.grid_array]
        }

        with open(self.raw_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(turn_log, separators=(",", ":")) + "\n")

        self.turn_count += 1

        if self.turn_count % self.flush_interval == 0:
            self.write_static_data()
            self.compress_log()

    def compress_log(self):
        """로그 파일 압축"""
        self.compress_count += 1
        compressed_file = os.path.join(self.compressed_dir, f"turn_logs_{self.compress_count:04d}.zst")

        cctx = zstd.ZstdCompressor(level=5)
        with open(self.raw_log_file, "rb") as in_f, open(compressed_file, "wb") as out_f:
            out_f.write(cctx.compress(in_f.read()))

        open(self.raw_log_file, "w").close()