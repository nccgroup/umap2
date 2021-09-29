#!/usr/bin/env python
'''
List default classes supported in umap

Usage:
    umap2list [-v]

Options:
    -v, --verbose   show more information
'''
from umap2.apps.base import Umap2App


class Umap2ListClassesApp(Umap2App):

    def run(self):
        ks = self.umap_classes
        verbose = self.options.get('--verbose', False)
        if verbose:
            print('%-20s  %s' % ('Device', 'Description'))
            print('--------------------  ----------------------------------------------------')
        for k in ks:
            if verbose:
                print('%-20s  %s' % (k, self.umap_class_dict[k][1]))
            else:
                print('%s' % k)


def main():
    app = Umap2ListClassesApp(__doc__)
    app.run()


if __name__ == '__main__':
    main()
