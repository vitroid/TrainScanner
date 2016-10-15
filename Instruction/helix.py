# helix
import math

stroke(0)
nofill()

r = 100

beginpath(r,r/3)
for i in range(0,360,6):
    th = i * math.pi / 180 - 1.3
    x = math.cos(th)
    y = -math.sin(th)
    sx  = r * x
    sy  = r * y/3.0
    lineto(sx+r,sy+r/3)
endpath()
stroke()


beginpath(r,r)
for i in range(0,6*360,6):
    th = i * math.pi / 180 - 1.3
    x = math.cos(th)
    y = -math.sin(th)
    sx  = r * x
    sy  = r * y/3 + i/5.0
    lineto(sx+r,sy+r)
endpath()
beginpath(r,r)
for i in range(0,6*360,6):
    th = i * math.pi / 180 - 1.3
    x = math.cos(th)
    y = -math.sin(th)
    sx  = r * x
    sy  = r * y/3 + i/5.0 + 10
    lineto(sx+r,sy+r)
endpath()
