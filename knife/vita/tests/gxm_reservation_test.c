/* Run the real native allocator against the existing explicit SDK doubles.
   Tests model physical-page failure, not real Vita fragmentation or timing. */
#define main compressed_boundary_main
#include "gxm_compressed_test.c"
#undef main

static void release_reservation(KvGxm *g) {
    EXPECT(block_free(g, &g->texture_reservation) == 0);
    EXPECT(pool_destroy(g) == 0);
    EXPECT(g->stats.cdram_mapped_bytes == 0);
    EXPECT(allocated == released);
}
int main(void) {
    for (unsigned pooled = 0; pooled < 2; ++pooled) {
        kv_render_set_options(pooled ? KV_OPT_TEXTURE_POOL : 0);
        KvGxm g;
        reset(&g, "real 1020x1016 RGBA admission and single ownership transfer");
        const uint32_t request = 1024U * 1016U * 4U;
        setup_upload(1020, 1016, 0, request, 0, 1);
        EXPECT(wanted_allocation == 4 * 1024 * 1024);
        EXPECT(kv_gxm_texture_reserve(&g, request) == 1);
        EXPECT(alloc_calls == 1 && allocated == wanted_allocation);
        EXPECT(g.stats.cdram_mapped_bytes == wanted_allocation);
        EXPECT(kv_gxm_texture_reserve(&g, request) == 1 && alloc_calls == 1);
        Block taken = {0};
        EXPECT(texture_pixels_alloc(&g, &taken, request) == 0);
        EXPECT(taken.uid == 41 && taken.base == backing && !g.texture_reservation.uid);
        EXPECT(alloc_calls == 1 && init_calls == 0);
        EXPECT(block_free(&g, &taken) == 0);
        release_reservation(&g);

        reset(&g, "reported free bytes cannot guarantee physical pages");
        setup_upload(1020, 1016, 0, request, 0, 1);
        fault = ALLOC; alloc_fault_code = (int)SCE_KERNEL_ERROR_NO_FREE_PHYSICAL_PAGE_CDRAM;
        uint32_t free_bytes = 0;
        EXPECT(kv_gxm_cdram_available(&g, &free_bytes) == 0 && free_bytes > request);
        EXPECT(kv_gxm_texture_reserve(&g, request) == 0);
        EXPECT(!g.closing && !g.texture_reservation.uid && !g.texture_pages && !g.textures);
        EXPECT(!g.stats.cdram_mapped_bytes && alloc_calls == 1);
        fault = NONE; alloc_fault_code = fault_code;
        EXPECT(kv_gxm_texture_reserve(&g, request) == 1 && alloc_calls == 2);
        release_reservation(&g);

        reset(&g, "page-rounded policy pressure stays recoverable");
        setup_upload(1020, 1016, 0, request, 0, 1);
        g.stats.cdram_mapped_bytes = CDRAM_LIMIT - g.stats.parameter_reserved_bytes - request;
        EXPECT(kv_gxm_texture_reserve(&g, request) == 0 && !alloc_calls);
        EXPECT(!g.closing && !g.texture_pages && !g.texture_reservation.uid);
        g.stats.cdram_mapped_bytes = 0;

        reset(&g, "mapping error never becomes retryable memory pressure");
        setup_upload(1020, 1016, 0, request, 0, 1);
        fault = MAP;
        EXPECT(kv_gxm_texture_reserve(&g, request) == fault_code);
        EXPECT(!g.closing && !g.texture_pages && !g.texture_reservation.uid);
        EXPECT(allocated == released && !g.stats.cdram_mapped_bytes);

        reset(&g, "different request releases one old reservation");
        setup_upload(1020, 1016, 0, request, 0, 1);
        EXPECT(kv_gxm_texture_reserve(&g, request) == 1);
        free_failure = 1;
        EXPECT(kv_gxm_texture_reserve(&g, request + ALIGNMENT) == free_code);
        EXPECT(g.closing && allocated && !released);
        free_failure = 0;
        release_reservation(&g);

        reset(&g, "invalid reservation cannot allocate or free storage");
        EXPECT(kv_gxm_texture_reserve(&g, 0) == KV_BAD_ARGUMENT);
        EXPECT(kv_gxm_texture_reserve(&g, UINT32_MAX) == KV_BAD_ARGUMENT);
        g.scene_open = 1;
        EXPECT(kv_gxm_texture_reserve(&g, 64) == KV_STATE);
        EXPECT(!alloc_calls && !free_calls);
    }
    kv_render_set_options(0);
    printf("RESULT %s: %u cases, %u checks, %u failures; actual allocator, SDK doubles, no hardware claim\n",
        failures ? "FAIL" : "PASS", cases, checks, failures);
    return failures ? 1 : 0;
}
