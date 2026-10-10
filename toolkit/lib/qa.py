"""QA helpers.
  python lib/qa.py sheet <video> <out.png> [cols rows]   -> contact sheet of evenly spaced frames
  python lib/qa.py frames <video> <outdir> t1 t2 ...       -> PNG frames at given times
  python lib/qa.py capframes <video> <timeline_all.json> <outdir> -> one frame per caption (midpoint)
  python lib/qa.py loud <video>                            -> ebur128 summary"""
import sys, os, subprocess, json
def dur(v): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",v]).decode())
def frame(v, t, out, w=None):
    vf = ["-vf", f"scale={w}:-1"] if w else []
    subprocess.run(["ffmpeg","-y","-v","error","-ss",f"{t:.3f}","-i",v,"-frames:v","1",*vf,out],check=True)
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "sheet":
        v, out = sys.argv[2], sys.argv[3]; c = int(sys.argv[4]) if len(sys.argv) > 4 else 3; r = int(sys.argv[5]) if len(sys.argv) > 5 else 3
        d = dur(v); n = c * r; tmp = out + "_tmp"; os.makedirs(tmp, exist_ok=True)
        for i in range(n): frame(v, d * (i + 0.5) / n, f"{tmp}/{i:03d}.png", 640)
        subprocess.run(["ffmpeg","-y","-v","error","-i",f"{tmp}/%03d.png","-vf",f"tile={c}x{r}:padding=6:color=black",out],check=True)
        subprocess.run(["rm","-rf",tmp]); print(out)
    elif cmd == "frames":
        v, od = sys.argv[2], sys.argv[3]; os.makedirs(od, exist_ok=True)
        for t in sys.argv[4:]: frame(v, float(t), f"{od}/f_{float(t):07.2f}.png", 1280)
    elif cmd == "capframes":
        v, tl, od = sys.argv[2:5]; os.makedirs(od, exist_ok=True)
        caps = json.load(open(tl))["captions"]
        for i, c in enumerate(caps): frame(v, (c["t"] + c["end"]) / 2, f"{od}/c{i:03d}.png", 960)
        print(len(caps), "frames")
    elif cmd == "loud":
        r = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",sys.argv[2],"-af","ebur128=peak=true","-f","null","-"],capture_output=True,text=True)
        print(r.stderr[r.stderr.rfind("Summary"):])
