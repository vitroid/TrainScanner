#only 34 frames
speed(30)

x=0
v = 0
a = 0

nframe = 0
size(500,500)
def draw():
    global nframe,a,v,x
    nframe+=1
    if nframe < 5:
        a = 0
    elif nframe < 20:
        a = 1
    else:
        a = -1
    v += a
    x += v
    stroke(0)
    nofill()
    strokewidth(30)
    print(v) 
    oval(x+50,50,400,400)
    oval(x+100,100,300,300)
    oval(x+150,150,200,200)
    oval(x+200,200,100,100)
