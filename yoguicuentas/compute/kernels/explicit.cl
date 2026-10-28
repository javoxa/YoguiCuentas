// OpenCL C 1.1. Differences avoid cancellation between absolute temperatures.
inline float heat_rate(int p, int nx, int ny, __global const float *t,
    __global const float *e, __global const float *w, __global const float *n,
    __global const float *s, __global const float *sink, __global const float *f,
    float reference)
{
    int x=p%nx,y=p/nx;
    float r=f[p]-sink[p]*(t[p]-reference);
    if(x<nx-1) r+=e[p]*(t[p+1]-t[p]);
    if(x>0) r+=w[p]*(t[p-1]-t[p]);
    if(y<ny-1) r+=n[p]*(t[p+nx]-t[p]);
    if(y>0) r+=s[p]*(t[p-nx]-t[p]);
    return r;
}
__kernel void explicit_heat(__global const float *t, __global float *out,
    __global const float *e, __global const float *w, __global const float *n,
    __global const float *s, __global const float *sink, __global const float *f,
    int nx,int ny,float dt,float reference,__global const uchar *active)
{
    int x=get_global_id(0),y=get_global_id(1);
    if(x>=nx || y>=ny) return;
    int p=y*nx+x;
    if(!active[p]) {out[p]=t[p];return;}
    out[p]=t[p]+dt*heat_rate(p,nx,ny,t,e,w,n,s,sink,f,reference);
}
__kernel void steady_residual(__global const float *t,
    __global const float *e, __global const float *w, __global const float *n,
    __global const float *s, __global const float *sink, __global const float *f,
    int nx,int ny,float reference,__global const float *weights,
    __global float *out,__local float2 *scratch)
{
    int i=get_local_id(0),size=get_local_size(0);
    float2 value=(float2)(0,0);
    for(int p=i;p<nx*ny;p+=size){
        float r=fabs(heat_rate(p,nx,ny,t,e,w,n,s,sink,f,reference));
        // Propagate nonfinite residuals rather than masking them with fmax.
        if(!isfinite(r)) r=INFINITY;
        value.x=fmax(value.x,r); value.y+=r*weights[p];
    }
    scratch[i]=value; barrier(CLK_LOCAL_MEM_FENCE);
    for(int stride=size/2;stride>0;stride/=2){
        if(i<stride){scratch[i].x=fmax(scratch[i].x,scratch[i+stride].x);
                     scratch[i].y+=scratch[i+stride].y;}
        barrier(CLK_LOCAL_MEM_FENCE);
    }
    if(i==0){out[0]=scratch[0].x;out[1]=scratch[0].y;}
}

// Direct stationary solver. dt is accepted for the common dispatch signature,
// but iterations have no associated physical time.
__kernel void stationary_jacobi(__global const float *t, __global float *out,
    __global const float *e, __global const float *w, __global const float *n,
    __global const float *s, __global const float *sink, __global const float *f,
    int nx,int ny,float dt,float reference,__global const uchar *active)
{
    int x=get_global_id(0),y=get_global_id(1);
    if(x>=nx || y>=ny) return;
    int p=y*nx+x;
    float diagonal=e[p]+w[p]+n[p]+s[p]+sink[p];
    if(!active[p] || diagonal<=0.0f) {out[p]=t[p];return;}
    float rate=heat_rate(p,nx,ny,t,e,w,n,s,sink,f,reference);
    out[p]=t[p]+(2.0f/3.0f)*(rate/diagonal);
}
