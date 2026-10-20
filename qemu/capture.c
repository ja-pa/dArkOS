/* Optional EGL frame capture for local QEMU tests. No effect without preload.
 * QEMU's GL scanout has no CPU surface for QMP screendump. Capture the actual
 * client framebuffer immediately before presentation instead. Remove this
 * helper when the tested QEMU can read back its VirGL scanout directly. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdint.h>

typedef void *Display;
typedef void *Surface;
typedef unsigned int Bool;
static void *egl_library(void) {
    static void *handle;
    if (!handle) handle=dlopen("libEGL.so.1",RTLD_LAZY|RTLD_LOCAL);
    return handle;
}
static void capture(Display d, Surface s) {
    if (access("/run/darkos-qemu/capture.request", F_OK)) return;
    Bool (*query)(Display,Surface,int,int*)=dlsym(egl_library(),"eglQuerySurface");
    void *(*proc)(const char*)=dlsym(egl_library(),"eglGetProcAddress");
    if (!query || !proc) return;
    void (*readpixels)(int,int,int,int,unsigned int,unsigned int,void*)=proc("glReadPixels");
    void (*pixelstore)(unsigned int,int)=proc("glPixelStorei");
    void (*getint)(unsigned int,int*)=proc("glGetIntegerv");
    int w=0,h=0,alignment=4;
    if (!readpixels || !pixelstore || !getint || !query(d,s,0x3057,&w) || !query(d,s,0x3056,&h)) return;
    if (w<1 || h<1 || w>8192 || h>8192) return;
    size_t stride=(size_t)w*3;
    unsigned char *pixels=malloc(stride*(size_t)h);
    if (!pixels) return;
    getint(0x0D05,&alignment); /* GL_PACK_ALIGNMENT */
    pixelstore(0x0D05,1);
    readpixels(0,0,w,h,0x1907,0x1401,pixels); /* GL_RGB, GL_UNSIGNED_BYTE */
    pixelstore(0x0D05,alignment);
    FILE *f=fopen("/run/darkos-qemu/frame.ppm.partial","wb");
    int ok=f!=NULL;
    if (f) {
        if (fprintf(f,"P6\n%d %d\n255\n",w,h)<0) ok=0;
        for (int y=h-1;y>=0;y--) if (fwrite(pixels+stride*(size_t)y,1,stride,f)!=stride) ok=0;
        if (fclose(f)) ok=0;
        if (ok && !rename("/run/darkos-qemu/frame.ppm.partial","/run/darkos-qemu/frame.ppm"))
            unlink("/run/darkos-qemu/capture.request");
    }
    free(pixels);
}
Bool eglSwapBuffers(Display d, Surface s) {
    static Bool (*swap)(Display,Surface);
    if (!swap) swap=dlsym(RTLD_NEXT,"eglSwapBuffers");
    if (!swap) return 0;
    capture(d,s);
    return swap(d,s);
}

/* SDL loads EGL entry points from a specific dlopen handle, so also interpose
 * the SDL presentation symbol used by ES. RetroArch's KMS EGL path uses the
 * eglSwapBuffers wrapper above. */
void SDL_GL_SwapWindow(void *window) {
    static void (*swap)(void*);
    if (!swap) swap=dlsym(RTLD_NEXT,"SDL_GL_SwapWindow");
    if (!access("/run/darkos-qemu/capture.request",F_OK)) {
        Display (*display)(void)=dlsym(egl_library(),"eglGetCurrentDisplay");
        Surface (*surface)(int)=dlsym(egl_library(),"eglGetCurrentSurface");
        if (display && surface) capture(display(),surface(0x3059));
    }
    if (swap) swap(window);
}
