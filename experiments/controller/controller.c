/* Procedural pilot SUT with separately controlled cycle stages. */
#include <assert.h>
#include <string.h>
typedef struct {
    int mode,on,count,left,right;
    int engine,hazard,direction;
    int sampled_engine,sampled_hazard,sampled_direction;
    int next_mode,next_on,next_count,next_left,next_right;
    int stage;
} Controller;
static int choose(int e,int h,int p,int bug) {
    if(bug==11)h=0;
    if(bug==4 && !e)return 0;
    if(bug==3 && e && p)return p;
    if(h)return 3;
    return e?p:0;
}
static void output(int m,int on,int *l,int *r,int bug) {
    *l=on&&(m==1||m==3)?100:0;
    *r=on&&(m==2||m==3)?100:0;
    if(bug==9){int t=*l;*l=*r;*r=t;}
    if(bug==12 && m==3)*r=0;
}

void reset(Controller *s){memset(s,0,sizeof(*s));}
void assign_inputs(Controller *s,int e,int h,int p){
    assert((e==0||e==1)&&(h==0||h==1)&&p>=0&&p<=2);
    s->engine=e;s->hazard=h;s->direction=p;
}
void sample(Controller *s){
    assert(s->stage==0);
    s->sampled_engine=s->engine;s->sampled_hazard=s->hazard;
    s->sampled_direction=s->direction;s->stage=1;
}
static void compute_pending(Controller *s,int e,int h,int p,int bug){
    int m=choose(e,h,p,bug),on=s->on,n=s->count;
    int reload=bug==1?3:bug==2?5:4;
    if(!m){on=0;n=0;}
    else if(!s->mode || (bug==5 && m!=s->mode)){on=1;n=reload;}
    else if(n){n--;}
    else{on=!on;n=reload;}
    s->next_mode=m;s->next_on=on;s->next_count=n;
    output(m,on,&s->next_left,&s->next_right,bug);
}
void decide(Controller *s,int bug){
    assert(s->stage==1);
    if(bug==6)compute_pending(s,s->engine,s->hazard,s->direction,bug);
    else compute_pending(s,s->sampled_engine,s->sampled_hazard,s->sampled_direction,bug);
    if(bug==8){s->left=s->next_left;s->right=s->next_right;}
    s->stage=2;
}
void emit(Controller *s,int bug){
    assert(s->stage==2);
    /* Fault 7 recomputes the response from live inputs at publication. */
    if(bug==7)compute_pending(s,s->engine,s->hazard,s->direction,bug);
    int previous_mode=s->mode;
    s->mode=s->next_mode;s->on=s->next_on;s->count=s->next_count;
    s->left=s->next_left;s->right=s->next_right;
    if(bug==10)output(previous_mode,s->on,&s->left,&s->right,0);
    s->stage=0;
}
