#!/usr/bin/env python
'''
List default classes supported in umap

Usage:
    umap2list
'''
from umap2.apps.base import Umap2App


class Umap2ListClassesApp(Umap2App):

    def run(self):
        ks = self.umap_classes
        for k in ks:
            print('%s' % k)


def main():
    app = Umap2ListClassesApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
