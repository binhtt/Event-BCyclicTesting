/* Independent procedural pilot SUT. No oracle tables are linked here. */
typedef struct { int mode,on,count,left,right; } Controller;
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
void reset(Controller *s){s->mode=s->on=s->count=s->left=s->right=0;}
/* Returns 1 when Decide changes externally visible output before Emit. */
int cycle(Controller *s,int e,int h,int p,int de,int dh,int dp,
          int ee,int eh,int ep,int bug) {
    int oldmode=s->mode, oldl=s->left, oldr=s->right;
    if(bug==6){e=de;h=dh;p=dp;}
    if(bug==7){e=ee;h=eh;p=ep;}
    int m=choose(e,h,p,bug),on=s->on,n=s->count;
    int reload=bug==1?3:bug==2?5:4;
    if(!m){on=0;n=0;}
    else if(!oldmode || (bug==5 && m!=oldmode)){on=1;n=reload;}
    else if(n){n--;}
    else{on=!on;n=reload;}
    int l,r;output(m,on,&l,&r,bug);
    if(bug==8){s->left=l;s->right=r;} /* faulty publication at Decide */
    int early=s->left!=oldl || s->right!=oldr;
    s->mode=m;s->on=on;s->count=n;
    if(bug!=10){s->left=l;s->right=r;}
    else { /* faulty output uses previous mode and current phase */
        output(oldmode,s->on,&s->left,&s->right,0);
    }
    return early;
}
