USAGE: grp <archiveName> <command> [options] [command] [options] ...
EXAMPLES: grp 3D -add model.3ds *.dds
          grp 3D -list *.png
          grp 3D -repack
          grp 3D -test
          grp 3D -unlink oldmodel*
          grp 3D -unpack *.3ds c:\models -force
          grp 3D -unlink oldmodel* -add newmodel* -repack

This program reads and writes archive files in the .ndx/.grp format used by
Sonalysts' simulation software.

ARCHIVE NAME
The archive name should be specified as the name or path of the archive files,
without the .ndx or .grp suffixes. For instance 3D or C:\data\3D.

COMMANDS
-add <specs>    Adds files matching the given file specifications to the
                archive. If the archive does not exist, it will be created.
-list [specs]   Lists files matching the given file specifications. If no file
                specs are given, all files in the archive are listed.
-repack         Repacks the archive to eliminate any unused space. This may be
                useful if many files were unlinked from the archive.
-test [specs]   Tests files matching the given file specifications to ensure
                that they can be decompressed without error.
-unlink <specs> Removes files from the archive. The space used by the files
                will not be reclaimed until the archive is repacked.
-unpack [specs] [dir]
                Unpacks files matching the given file specifications from the
                archive and stores them in the given directory. If no file
                specs are given, all files are unpacked. If no directory is
                given, the files are unpacked into the current directory.
-? -help /?     Displays this help message.

OPTIONS
-force          When specified, the -add and -unpack commands will overwrite
                existing files without warning.

FILE SPECIFICATIONS
A file specification is the name of a file (when referencing a file within the
archive) or an absolute or relative path to a file (when referencing a file on
disk). File specifications can contain the standard wildcards within the file
name part; an asterisk (*) will match multiple characters and a question mark
will match a single character. Wild cards must not be used within the
directory part. Names with spaces should be enclosed in quotation marks.

Good examples: *.png model.* file??.ext c:\path\* "big boat.3ds"
Bad example: c:\models\ffg*\*.3ds

OTHER REMARKS
Commands are executed in the order given. When adding and unlinking files, it
is usually better to unlink old files before adding new ones, so that the new
files can fit within the space freed up by the unlinked files. However, if you
will repack the archive anyway, this is not so important.
