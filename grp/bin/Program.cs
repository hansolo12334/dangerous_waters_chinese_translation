/*
grp is a program to read, create, and modify .ndx/.grp archive files used by
Sonalysts' simulation software. It is part of the DWMU (Dangerous Waters Mod
Utilities) package.

http://www.adammil.net/
Copyright (C) 2011 Adam Milazzo

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*/

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using AdamMil.IO;
using AdamMil.Utilities;

namespace grp
{
  class Program
  {
    sealed class Command
    {
      public Command(CommandType type, string[] args)
      {
        Type = type;
        Args = args;
      }

      public readonly CommandType Type;
      public readonly string[] Args;
    }

    enum CommandType
    {
      Invalid, Add, List, Repack, Test, Unlink, Unpack
    }

    static int Main(string[] args)
    {
      if(!ParseArguments(args))
      {
        ShowHelp(false);
        return 2;
      }

      try
      {
        int returnValue = 0;
        foreach(Command command in commands)
        {
          if(!ExecuteCommand(command))
          {
            returnValue = 1;
            break;
          }
        }

        if(!SaveArchive()) returnValue = 1;
        return returnValue;
      }
      finally
      {
        if(archive != null) archive.Dispose();
      }
    }

    static bool AddFiles(string[] fileSpecs)
    {
      if(OpenArchive(true))
      {
        Console.WriteLine("Adding files...");
        HashSet<string> names = force ? null : new HashSet<string>(archive.IndexEntries.Select(e => e.Name.ToLowerInvariant()));
        bool added = false, failed = false;
        foreach(string fileSpec in fileSpecs)
        {
          string[] filePaths;
          if(fileSpec.Contains('*') || fileSpec.Contains('?'))
          {
            string directory = Path.GetDirectoryName(fileSpec), wildcard = Path.GetFileName(fileSpec);

            if(!string.IsNullOrEmpty(directory) && (directory.Contains('*') || directory.Contains('?')))
            {
              failed = true;
              Console.WriteLine("ERROR: File spec " + fileSpec + " contains a wildcard in a directory name.");
              continue;
            }

            filePaths = PathUtility.GetFiles(string.IsNullOrEmpty(directory) ? Environment.CurrentDirectory : directory, wildcard);
          }
          else
          {
            filePaths = new string[] { fileSpec };
          }

          foreach(string filePath in filePaths)
          {
            string fileName = Path.GetFileName(filePath);
            Console.Write(filePath);
            if(!File.Exists(filePath))
            {
              Console.WriteLine(" failed! File does not exist.");
              failed = true;
            }
            else if(fileName.Length > 79)
            {
              Console.WriteLine(" failed! Name is too long. The maximum is 79 characters.");
              failed = true;
            }
            else
            {
              if(!force && names.Contains(fileName.ToLowerInvariant()) && !ShouldOverwrite()) continue;
              Console.Write("...");

              try
              {
                using(FileStream file = File.OpenRead(filePath))
                {
                  if(file.Length > int.MaxValue)
                  {
                    Console.WriteLine(" Failed! File is too big.");
                    continue;
                  }

                  // if the file may be a bitmap, try to extract the size
                  uint pixelWidth = 0, pixelHeight = 0;
                  try
                  {
                    if(Path.GetExtension(filePath).OrdinalEquals(".bmp", true) && file.ReadBE2U() == 0x424D)
                    {
                      byte[] data = new byte[24];
                      int read = file.FullRead(data, 0, 24);
                      if(read == 24) // if we could read the file header and part of the bitmap header...
                      {
                        int headerSize = IOH.ReadLE4(data, 12); // get the bitmap header size...
                        if(headerSize == 12 || headerSize == 40 || headerSize == 108 || headerSize == 124 ||
                           headerSize == 52 || headerSize == 56) // if it's a recognized BMP header size...
                        {
                          pixelWidth  = IOH.ReadLE4U(data, 16); // read the dimensions
                          pixelHeight = IOH.ReadLE4U(data, 20);
                          if(pixelWidth > 65535 || pixelHeight > 65535) pixelWidth = pixelHeight = 0; // sanity check them
                        }
                      }
                    }
                  }
                  finally
                  {
                    file.Position = 0;
                  }

                  archive.Add(fileName, file, pixelWidth, pixelHeight);
                  if(names != null) names.Add(fileName.ToLowerInvariant());
                  Console.WriteLine(" OK.");
                  added = true;
                }
              }
              catch(IOException ex)
              {
                Console.WriteLine(" Failed! " + ex.Message);
                failed = true;
              }
            }
          }
        }

        if(!failed && !added) Console.WriteLine("WARN: No files added.");
        if(!failed) return true;
      }

      return false;
    }

    static bool ExecuteCommand(Command command)
    {
      try
      {
        switch(command.Type)
        {
          case CommandType.Add: return AddFiles(command.Args);
          case CommandType.List: return ListFiles(command.Args);
          case CommandType.Repack: return RepackFiles();
          case CommandType.Test: return TestFiles(command.Args);
          case CommandType.Unlink: return UnlinkFiles(command.Args);
          case CommandType.Unpack: return UnpackFiles(command.Args);
        }
      }
      catch(Exception ex)
      {
        Console.WriteLine("ERROR: " + ex.Message);
      }

      return false;
    }

    static bool ListFiles(string[] fileSpecs)
    {
      if(OpenArchive())
      {
        Regex[] regexes = ParseFileSpecs(fileSpecs);
        Console.WriteLine("      Size Compressed Name");
        Console.WriteLine("---------- ---------- --------------------------------------------------------");

        bool matched = false;
        foreach(NdxEntry entry in archive.IndexEntries)
        {
          if(MatchesFileSpec(entry.Name, regexes))
          {
            Console.WriteLine(entry.UncompressedSize.ToString().PadLeft(10, ' ') + " " +
                              entry.CompressedSize.ToString().PadLeft(10, ' ') + " " + entry.Name);
            matched = true;
          }
        }

        if(!matched) Console.WriteLine("No matching files could be found in the archive.");
        return true;
      }

      return false;
    }

    static bool MatchesFileSpec(string name, Regex[] regexes)
    {
      foreach(Regex regex in regexes)
      {
        if(regex.IsMatch(name)) return true;
      }
      return regexes.Length == 0;
    }

    static bool OpenArchive()
    {
      return OpenArchive(false);
    }

    static bool OpenArchive(bool create)
    {
      if(archive == null)
      {
        string ndxFileName = archiveName + ".ndx", grpFileName = archiveName + ".grp";
        if(!File.Exists(ndxFileName) || !File.Exists(grpFileName))
        {
          string extension = Path.GetExtension(archiveName).ToLowerInvariant();
          if(extension == ".ndx" || extension == ".grp")
          {
            string baseName = Path.Combine(Path.GetDirectoryName(archiveName), Path.GetFileNameWithoutExtension(archiveName));
            ndxFileName = baseName + ".ndx";
            grpFileName = baseName + ".grp";
          }
        }

        if(!create)
        {
          if(!File.Exists(ndxFileName))
          {
            Console.WriteLine("ERROR: Unable to find .ndx file " + ndxFileName);
            return false;
          }

          if(!File.Exists(grpFileName))
          {
            Console.WriteLine("ERROR: Unable to find .grp file " + grpFileName);
            return false;
          }
        }

        FileMode mode = create ? FileMode.OpenOrCreate : FileMode.Open;
        try
        {
          archive = new GrpFile(File.Open(ndxFileName, mode, FileAccess.ReadWrite),
                                File.Open(grpFileName, mode, FileAccess.ReadWrite), true);
        }
        catch(InvalidDataException ex)
        {
          Console.WriteLine("ERROR: This may not be a Sonalysts archive, or the archive may be corrupt. " + ex.Message);
        }
        catch(IOException ex)
        {
          Console.WriteLine("ERROR: Unable to read from the archive. It may be in use by another program. " + ex.Message);
        }
      }

      return archive != null;
    }

    static bool ParseArguments(string[] args)
    {
      bool failed = false, showFullHelp = false;

      List<Command> commands = new List<Command>();
      int i = 0;
      if(args.Length == 0 || args[0].Length == 0)
      {
        Console.WriteLine("ERROR: No archive name was specified.");
        failed = true;
      }
      else if(args[0][0] != '-' && args[0][0] != '/')
      {
        archiveName = args[0];
        i = 1;
      }

      while(i < args.Length)
      {
        string arg = args[i];
        if(arg.Length != 0 && (arg[0] == '-' || arg[0] == '/'))
        {
          CommandType type = CommandType.Invalid;
          switch(arg.Substring(1).ToLowerInvariant())
          {
            case "add": type = CommandType.Add; break;
            case "list": type = CommandType.List; break;
            case "repack": type = CommandType.Repack; break;
            case "test": type = CommandType.Test; break;
            case "unlink": type = CommandType.Unlink; break;
            case "unpack": type = CommandType.Unpack; break;
            case "force": force = true; break;
            case "help": case "?": case "-help": showFullHelp = true; break;
            default:
              Console.WriteLine("ERROR: Invalid command: " + arg);
              failed = true;
              break;
          }

          List<string> files = new List<string>();
          for(i++; i<args.Length && args[i].Length != 0 && args[i][0] != '-' && args[i][0] != '/'; i++) files.Add(args[i]);

          if(files.Count == 0 && (type == CommandType.Add || type == CommandType.Unlink))
          {
            Console.WriteLine("ERROR: -" + (type == CommandType.Add ? "add" : "unlink") + " requires file specifications.");
            failed = true;
          }

          commands.Add(new Command(type, files.ToArray()));
        }
        else
        {
          Console.WriteLine("ERROR: Invalid command: " + args[i]);
          i++;
          failed = true;
        }
      }

      if(showFullHelp)
      {
        ShowHelp(true);
        commands.Clear();
      }
      else if(!failed && commands.Count == 0)
      {
        Console.WriteLine("ERROR: No commands were given.");
        failed = true;
      }

      Program.commands = commands.ToArray();
      return !failed;
    }

    static Regex[] ParseFileSpecs(string[] fileSpecs)
    {
      return ParseFileSpecs(fileSpecs, fileSpecs.Length);
    }

    static Regex[] ParseFileSpecs(string[] fileSpecs, int count)
    {
      Regex[] regexes = new Regex[count];
      for(int i=0; i<count; i++)
      {
        regexes[i] = new Regex("^" + fileSpecRe.Replace(fileSpecs[i], m =>
        {
          if(m.Length == 1)
          {
            char c = m.Value[0];
            if(c == '*') return ".*?";
            else if(c == '?') return ".";
            else if(c == '/' || c == '\\') return @"[/\\]";
          }
          return Regex.Escape(m.Value);
        }) + "$", RegexOptions.Singleline | RegexOptions.IgnoreCase);
      }
      return regexes;
    }

    static bool RepackFiles()
    {
      if(OpenArchive())
      {
        Console.WriteLine("Scheduling repack.");
        archive.Repack();
        return true;
      }
      return false;
    }

    static bool SaveArchive()
    {
      if(archive != null && archive.WasModified)    
      {
        try
        {
          Console.Write("Saving changes... ");
          archive.Save();
          Console.WriteLine("done.");
        }
        catch(Exception ex)
        {
          Console.WriteLine("ERROR: Failed to save archive. " + ex.Message);
          return false;
        }
      }
      return true;
    }

    static bool ShouldOverwrite()
    {
      Console.Write(" exists. Overwrite (Yes, No, All)? ");
      while(true)
      {
        ConsoleKeyInfo key = Console.ReadKey(true);
        switch(char.ToLowerInvariant(key.KeyChar))
        {
          case 'a': force = true; return true;
          case 'n': Console.WriteLine(); return false;
          case 'y': return true;
        }
      }
    }

    static void ShowHelp(bool fullHelp)
    {
      Console.WriteLine("USAGE: grp <archiveName> <command> [options] [command] [options] ...");
      Console.Write("EXAMPLES: grp 3D -add model.3ds *.dds\n" +
                    "          grp 3D -list *.png\n" +
                    "          grp 3D -repack\n" +
                    "          grp 3D -test\n" +
                    "          grp 3D -unlink oldmodel*\n" +
                    "          grp 3D -unpack *.3ds c:\\models -force\n" +
                    "          grp 3D -unlink oldmodel* -add newmodel* -repack\n");
      if(!fullHelp)
      {
        Console.WriteLine("For more details, use grp -?");
      }
      else
      {
        Console.WriteLine(@"
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

Good examples: *.png model.* file??.ext c:\path\* ""big boat.3ds""
Bad example: c:\models\ffg*\*.3ds

OTHER REMARKS
Commands are executed in the order given. When adding and unlinking files, it
is usually better to unlink old files before adding new ones, so that the new
files can fit within the space freed up by the unlinked files. However, if you
will repack the archive anyway, this is not so important.");
      }
    }

    static bool TestFiles(string[] fileSpecs)
    {
      if(OpenArchive())
      {
        Regex[] regexes = ParseFileSpecs(fileSpecs);

        Console.WriteLine("Testing archive.");
        bool matched = false;
        foreach(NdxEntry entry in archive.IndexEntries)
        {
          if(MatchesFileSpec(entry.Name, regexes))
          {
            Console.Write(entry.Name + "...");
            try
            {
              long length = 0;
              using(Stream stream = archive.OpenFile(entry)) stream.Process((a, len) => { length += len; return true; });
              if(length != entry.UncompressedSize) Console.WriteLine(" FAILED! Length is incorrect.");
              else Console.WriteLine(" OK.");
            }
            catch(InvalidDataException)
            {
              Console.WriteLine(" FAILED! Data is corrupt.");
            }

            matched = true;
          }
        }

        if(!matched) Console.WriteLine("No matching files could be found in the archive.");
        return true;
      }

      return false;
    }

    static bool UnlinkFiles(string[] fileSpecs)
    {
      if(OpenArchive())
      {
        Regex[] regexes = ParseFileSpecs(fileSpecs);
        List<NdxEntry> entriesToUnlink = archive.IndexEntries.Where(e => MatchesFileSpec(e.Name, regexes)).ToList();
        foreach(NdxEntry entry in entriesToUnlink)
        {
          archive.Unlink(entry);
          Console.WriteLine(entry.Name + " unlinked.");
        }
        if(entriesToUnlink.Count == 0) Console.WriteLine("No matching files could be found in the archive.");
        return true;
      }

      return false;
    }

    static bool UnpackFiles(string[] fileSpecs)
    {
      if(OpenArchive())
      {
        string directory = null;
        if(fileSpecs.Length != 0 && Directory.Exists(fileSpecs[fileSpecs.Length-1])) directory = fileSpecs[fileSpecs.Length-1];

        Regex[] regexes = ParseFileSpecs(fileSpecs, fileSpecs.Length - (directory == null ? 0 : 1));

        Console.WriteLine("Unpacking archive.");
        bool matched = false;
        foreach(NdxEntry entry in archive.IndexEntries)
        {
          if(MatchesFileSpec(entry.Name, regexes))
          {
            matched = true;
            Console.Write(entry.Name);

            string outputFileName = directory == null ? entry.Name : Path.Combine(directory, entry.Name);
            if(!force && File.Exists(outputFileName) && !ShouldOverwrite()) goto skip;
            Console.Write("...");

            try
            {
              using(FileStream outFile = File.OpenWrite(outputFileName))
              using(Stream inStream = archive.OpenFile(entry))
              {
                inStream.CopyTo(outFile);
                outFile.Flush(); //hansolo
                if(outFile.Length != entry.UncompressedSize) Console.WriteLine(" FAILED! Length is incorrect.");
                else Console.WriteLine(" OK.");
              }
            }
            catch(InvalidDataException)
            {
              Console.WriteLine(" FAILED! Data is corrupt.");
            }
            catch(IOException ex)
            {
              Console.WriteLine(" FAILED! " + ex.Message);
            }
          }

          skip:;
        }

        if(!matched) Console.WriteLine("No matching files could be found in the archive.");
        return true;
      }

      return false;
    }

    static GrpFile archive;
    static Command[] commands;
    static string archiveName;
    static Regex fileSpecRe = new Regex(@"[/\\]|\*|\?|[^/\\\*\?]+", RegexOptions.Singleline);
    static bool force;
  }
}
