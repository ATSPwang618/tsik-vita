/* Tsukihime ships authored GXP in eboot. No runtime compiler/cache/module I/O.
 * Registration, patching and optional capability rejection stay in the backend. */
#include "runtime_shaders.h"
#include "diagnostic_log.h"
#include <psp2/kernel/clib.h>
extern const SceGxmProgram *kv_gxm_offline_effect_program(uint32_t shader);

int kv_runtime_shader_initialize(void) {
    KV_DIAGNOSTIC_PRINTF("[knife-shader] stage=initialize mode=offline runtime_compile=0 cache_io=0\n");
    return 1;
}
const SceGxmProgram *kv_runtime_shader_program(uint32_t shader) {
    /* Preserve the existing optional capability IDs and their exact fallbacks.
       Private material variants are chosen by the backend after validation. */
    if (shader == 11 || shader == 15 || (shader >= 17 && shader <= 23)
        || shader == 25 || shader == 26 || shader == 28 || (shader >= 32 && shader < 48))
        return kv_gxm_offline_effect_program(shader);
    return NULL;
}
int kv_runtime_shader_available(uint32_t shader) { return kv_runtime_shader_program(shader) != NULL; }
void kv_runtime_shader_shutdown(void) { /* Immutable embedded programs have no heap owner. */ }
