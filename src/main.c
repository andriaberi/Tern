#include <stdio.h>
#include <string.h>

#include "tern.h"

static void print_usage(FILE *out) {
    fprintf(out, "usage: tern [--help] [--version] <file.tn>\n");
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage(stderr);
        return 1;
    }

    const char *arg = argv[1];
    if (strcmp(arg, "--version") == 0) {
        printf("tern %s\n", TERN_VERSION);
        return 0;
    }
    if (strcmp(arg, "--help") == 0) {
        print_usage(stdout);
        return 0;
    }
    if (arg[0] == '-') {
        fprintf(stderr, "error: unknown option '%s'\n", arg);
        print_usage(stderr);
        return 1;
    }

    fprintf(stderr, "error: compilation is not implemented yet\n");
    return 1;
}
