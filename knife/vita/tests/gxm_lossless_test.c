/* Production C packing/readback + explicit SDK doubles, no hardware claim. */
#define main compressed_boundary_main
#include "gxm_compressed_test.c"
#undef main

static void packed(unsigned format,unsigned pooled,enum Fault point) {
    KvGxm g; reset(&g,"lossless RGB24 / alpha palette with real allocation ownership");
    kv_render_set_options(pooled ? KV_OPT_TEXTURE_POOL : 0); linear_test=1;
    const uint32_t w=509,h=400,pitch=(w+7)&~7U,source_stride=w*4+12;
    const uint32_t bpp=format==3 ? 1 : 3;
    const uint32_t palette_offset=(pitch*h+63)&~63U;
    const uint32_t bytes=format==3 ? palette_offset+1024 : pitch*h*bpp;
    setup_upload(w,h,format==3 ? SCE_GXM_TEXTURE_FORMAT_P8_ABGR : SCE_GXM_TEXTURE_FORMAT_U8U8U8_BGR,bytes,0,1);
    wanted_palette_offset=palette_offset;
    for (uint32_t y=0;y<h;++y) for(uint32_t x=0;x<w;++x) {
        uint8_t *p=input+y*source_stride+x*4;
        p[0]=(uint8_t)(x%256);p[1]=37;p[2]=91;p[3]=format==3 ? (uint8_t)(x%256) : 255;
    }
    fault=point;
    KvGxmTexture *t=NULL;
    if (point==NONE) EXPECT(kv_gxm_texture_reserve(&g,bytes)==1);
    int rc=kv_gxm_texture_create_ex(&g,input,w,h,source_stride,format,0,1,0,&t);
    if(point!=NONE) {
        EXPECT(rc==fault_code && !t && !g.textures && !g.closing);
    }else if (rc==0 && t) {
        EXPECT(t->bpp==bpp && t->pitch==pitch && t->palette_offset==(format==3 ? palette_offset : 0));
        EXPECT(alloc_calls==1 && palette_calls==(format==3));
        uint8_t *out=malloc(w*h*4); EXPECT(out!=NULL);
        if(out) {
            EXPECT(kv_gxm_texture_read(&g,t,out,w*h*4)==0);
            int exact=1;
            for(uint32_t y=0;y<h;++y) for(uint32_t x=0;x<w;++x) {
                const uint8_t *src=input+y*source_stride+x*4;
                const uint32_t read_bpp=format==3 ? 4 : 3;
                const uint8_t *dst=out+(y*w+x)*read_bpp;
                if(memcmp(src,dst,read_bpp)) exact=0;
            }
            EXPECT(exact); free(out);
        }
        int zero=1;
        for(uint32_t y=0;y<h;++y) for(uint32_t x=w*bpp;x<pitch*bpp;++x)
            if(backing[y*pitch*bpp+x]) zero=0;
        for(uint32_t i=format==3 ? bytes : pitch*h*bpp;i<t->pixels.size;++i) if(backing[i]) zero=0;
        EXPECT(zero);
        EXPECT(kv_gxm_texture_update(&g,t,0,0,1,1,input,4)==KV_BAD_ARGUMENT);
        EXPECT(kv_gxm_texture_destroy(&g,t)==0);
    }else { EXPECT(rc==0 && t); }
    EXPECT(block_free(&g,&g.texture_reservation)==0 && pool_destroy(&g)==0);
    EXPECT(allocated==released && !g.stats.cdram_mapped_bytes && !unexpected_calls);
}
static void rejected(void) {
    KvGxm g; reset(&g,"reject lossy palette and RGB alpha before allocation");
    for(unsigned i=0;i<257;++i) { uint32_t color=i;memcpy(input+i*4,&color,4); }
    KvGxmTexture *t=NULL;
    EXPECT(kv_gxm_texture_create_ex(&g,input,257,1,1028,3,0,1,0,&t)==KV_BAD_ARGUMENT);
    EXPECT(kv_gxm_texture_create_ex(&g,input,257,1,1028,2,0,1,0,&t)==KV_BAD_ARGUMENT);
    EXPECT(!t && !alloc_calls && !g.textures);
}
int main(void) {
    for(unsigned pooled=0;pooled<2;++pooled) for(unsigned format=2;format<=3;++format) {
        packed(format,pooled,NONE);
        for(enum Fault point=ALLOC;point<=CLAMP_V;++point) packed(format,pooled,point);
        if(format==3) packed(format,pooled,PALETTE);
    }
    rejected(); kv_render_set_options(0);
    printf("RESULT %s: %u cases, %u checks, %u failures; exact C bytes, SDK doubles, no hardware claim\n",failures ? "FAIL":"PASS",cases,checks,failures);
    return failures ? 1 : 0;
}
