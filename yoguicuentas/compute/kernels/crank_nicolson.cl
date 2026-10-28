// CN increment equation: (I + theta*dt*A) delta = dt*(f - A*T).
inline float cn_rate(int p,int nx,int ny,__global const float *delta,
    __global const float *e,__global const float *w,__global const float *n,
    __global const float *s,__global const float *sink)
{
    int x=p%nx,y=p/nx;float t=delta[p],r=-sink[p]*t;
    if(x<nx-1)r+=e[p]*(delta[p+1]-t);if(x>0)r+=w[p]*(delta[p-1]-t);
    if(y<ny-1)r+=n[p]*(delta[p+nx]-t);if(y>0)r+=s[p]*(delta[p-nx]-t);
    return r;
}
__kernel void cn_init(__global const float *t,__global float *a,__global float *b,__global float *rhs,
    __global const float *e,__global const float *w,__global const float *n,
    __global const float *s,__global const float *sink,__global const float *f,
    int nx,int ny,float dt,float reference)
{
    int p=get_global_id(0);if(p>=nx*ny)return;
    a[p]=0;b[p]=0;rhs[p]=dt*heat_rate(p,nx,ny,t,e,w,n,s,sink,f,reference);
}
__kernel void cn_iterate(__global const float *a,__global float *b,__global const float *rhs,
    __global const float *e,__global const float *w,__global const float *n,
    __global const float *s,__global const float *sink,__global const float *f,
    int nx,int ny,float theta_dt)
{
    int p=get_global_id(0);if(p>=nx*ny)return;
    float d=1+theta_dt*(e[p]+w[p]+n[p]+s[p]+sink[p]);
    float r=rhs[p]-a[p]+theta_dt*cn_rate(p,nx,ny,a,e,w,n,s,sink);
    b[p]=a[p]+(2.0f/3.0f)*r/d;
}
__kernel void cn_residual(__global const float *a,__global const float *rhs,
    __global const float *e,__global const float *w,__global const float *n,
    __global const float *s,__global const float *sink,__global const float *f,
    int nx,int ny,float theta_dt,__global float2 *out,__local float2 *scratch)
{
    int p=get_global_id(0),i=get_local_id(0),size=get_local_size(0);
    float2 v=(float2)(0,0);
    if(p<nx*ny){
        float r=fabs(rhs[p]-a[p]+theta_dt*cn_rate(p,nx,ny,a,e,w,n,s,sink));
        v=(float2)(isfinite(r)?r:INFINITY,isfinite(rhs[p])?fabs(rhs[p]):INFINITY);
    }
    scratch[i]=v;barrier(CLK_LOCAL_MEM_FENCE);
    for(int stride=size/2;stride>0;stride/=2){
        if(i<stride)scratch[i]=fmax(scratch[i],scratch[i+stride]);
        barrier(CLK_LOCAL_MEM_FENCE);
    }
    if(i==0)out[get_group_id(0)]=scratch[0];
}
__kernel void cn_accept(__global const float *t,__global const float *delta,__global float *out,int count)
{
    int p=get_global_id(0);if(p<count)out[p]=t[p]+delta[p];
}
