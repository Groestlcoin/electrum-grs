#!/bin/bash

# This script can be used on Linux hosts to build native libzbar binaries.
# sudo apt-get install pkg-config libx11-dev libx11-6 libv4l-dev libxv-dev libxext-dev libjpeg-dev
#
# It can also be used to cross-compile to Windows:
# $ sudo apt-get install mingw-w64 mingw-w64-tools win-iconv-mingw-w64-dev
# For a Windows x86 (32-bit) target, run:
# $ GCC_TRIPLET_HOST="i686-w64-mingw32" BUILD_TYPE="wine" ./contrib/make_zbar.sh
# Or for a Windows x86_64 (64-bit) target, run:
# $ GCC_TRIPLET_HOST="x86_64-w64-mingw32" BUILD_TYPE="wine" ./contrib/make_zbar.sh

ZBAR_VERSION="bb05ec54eec57f8397cb13fb9161372a281a1219"
# ^ tag 0.23.93

set -e

. "$(dirname "$0")/build_tools_util.sh" || (echo "Could not source build_tools_util.sh" && exit 1)

here="$(dirname "$(realpath "$0" 2> /dev/null || grealpath "$0")")"
CONTRIB="$here"
PROJECT_ROOT="$CONTRIB/.."

pkgname="zbar"
info "Building $pkgname..."

(
    cd "$CONTRIB"
    if [ ! -d zbar ]; then
        git clone https://github.com/mchehab/zbar.git
    fi
    cd zbar
    if ! $(git cat-file -e ${ZBAR_VERSION}) ; then
        info "Could not find requested version $ZBAR_VERSION in local clone; fetching..."
        git fetch --all
    fi
    git reset --hard
    git clean -dfxq
    git checkout "${ZBAR_VERSION}^{commit}"

    if [ "$BUILD_TYPE" = "wine" ] ; then
        echo "libzbar_la_LDFLAGS += -Wc,-static" >> zbar/Makefile.am
        echo "LDFLAGS += -Wc,-static" >> Makefile.am
    fi
    if ! [ -x configure ] ; then
        autoreconf -vfi || fail "Could not run autoreconf for $pkgname. Please make sure you have automake and libtool installed, and try again."
    fi
    if ! [ -r config.status ] ; then
        if [ "$BUILD_TYPE" = "wine" ] ; then
            # windows target
            AUTOCONF_FLAGS="$AUTOCONF_FLAGS \
                --with-x=no \
                --enable-video=yes \
                --with-jpeg=no \
                --with-directshow=yes \
                --disable-dependency-tracking"
        elif [ $(uname) == "Darwin" ]; then
            # macos target
            if ! command -v brew >/dev/null 2>&1; then
            fail "Homebrew not found. Install Homebrew or adjust the script."
            fi
            brew list --versions libiconv >/dev/null 2>&1 || brew install libiconv
            brew list --versions gettext  >/dev/null 2>&1 || brew install gettext

            LIBICONV_PREFIX="$(brew --prefix libiconv)"
            GETTEXT_PREFIX="$(brew --prefix gettext)"

            # Help configure find headers/libs from keg-only formulae
            export CPPFLAGS="${CPPFLAGS:-} -I${LIBICONV_PREFIX}/include -I${GETTEXT_PREFIX}/include"
            export LDFLAGS="${LDFLAGS:-} -L${LIBICONV_PREFIX}/lib -L${GETTEXT_PREFIX}/lib"
            export PKG_CONFIG_PATH="${PKG_CONFIG_PATH:-}:${GETTEXT_PREFIX}/lib/pkgconfig"
            AUTOCONF_FLAGS="$AUTOCONF_FLAGS \
                --with-x=no \
                --enable-video=no \
                --with-libiconv-prefix=${LIBICONV_PREFIX} \
                --with-libintl-prefix=${GETTEXT_PREFIX} \
                --with-jpeg=no"
        else
            # linux target
            AUTOCONF_FLAGS="$AUTOCONF_FLAGS \
                --with-x=yes \
                --enable-video=yes \
                --with-jpeg=yes"
        fi
        ./configure \
            $AUTOCONF_FLAGS \
            --prefix="$here/$pkgname/dist" \
            --enable-pthread=no \
            --enable-doc=no \
            --with-python=no \
            --with-gtk=no \
            --with-qt=no \
            --with-java=no \
            --with-imagemagick=no \
            --with-dbus=no \
            --enable-codes=qrcode \
            --disable-static \
            --enable-shared || fail "Could not configure $pkgname. Please make sure you have a C compiler installed and try again."
    fi
    make "-j$CPU_COUNT" || fail "Could not build $pkgname"
    make install || fail "Could not install $pkgname"
    . "$here/$pkgname/dist/lib/libzbar.la"
    host_strip "$here/$pkgname/dist/lib/$dlname"
    cp -fpv "$here/$pkgname/dist/lib/$dlname" "$PROJECT_ROOT/electrum_grs" || fail "Could not copy the $pkgname binary to its destination"
    info "$dlname has been placed in the inner 'electrum_grs' folder."
    if [ -n "$DLL_TARGET_DIR" ] ; then
        cp -fpv "$here/$pkgname/dist/lib/$dlname" "$DLL_TARGET_DIR/" || fail "Could not copy the $pkgname binary to DLL_TARGET_DIR"
    fi
)
