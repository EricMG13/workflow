import pstats, sys, io
p = pstats.Stats(sys.argv[1])
for name in sys.argv[2:]:
    s = io.StringIO(); pstats.Stats(sys.argv[1], stream=s).print_callers(name); print("\n".join(l for l in s.getvalue().splitlines() if "<-" in l or "src/" in l)[:3000])
