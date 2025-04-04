using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.IO.Compression;
using System.Linq;
using AdamMil.IO;
using AdamMil.IO.Compression;
using AdamMil.Utilities;

namespace grp
{
    public sealed class NdxEntry
    {
        
        public NdxEntry(uint offset, uint size) { Offset = offset; CompressedSize = size; }
        public NdxEntry(byte[] data)
        {
            Offset = IOH.ReadLE4U(data, 80);
            UncompressedSize = IOH.ReadLE4U(data, 84);
            CompressedSize = IOH.ReadLE4U(data, 88);
            PixelWidth = IOH.ReadLE4U(data, 92);
            PixelHeight = IOH.ReadLE4U(data, 96);
            int nameLength;
            for (nameLength = 0; nameLength < 80 && data[nameLength] != 0; nameLength++) { }
            Name = System.Text.Encoding.ASCII.GetString(data, 0, nameLength);
        }

        public string Name;
        public uint CompressedSize, Offset, UncompressedSize, PixelWidth, PixelHeight;

        public byte[] ToByteArray()
        {
            byte[] data = new byte[100];
            Array.Clear(data, 0, data.Length);
            System.Text.Encoding.ASCII.GetBytes(Name, 0, Name.Length, data, 0);
            IOH.WriteLE4U(data, 80, Offset);
            IOH.WriteLE4U(data, 84, UncompressedSize);
            IOH.WriteLE4U(data, 88, CompressedSize);
            IOH.WriteLE4U(data, 92, PixelWidth);
            IOH.WriteLE4U(data, 96, PixelHeight);
            return data;
        }

        public void Save(byte[] data)
        {
            int nameLength = System.Text.Encoding.ASCII.GetBytes(Name, 0, Name.Length, data, 0);
            Array.Clear(data, nameLength, 80-nameLength);
            IOH.WriteLE4U(data, 80, Offset);
            IOH.WriteLE4U(data, 84, UncompressedSize);
            IOH.WriteLE4U(data, 88, CompressedSize);
            IOH.WriteLE4U(data, 92, PixelWidth);
            IOH.WriteLE4U(data, 96, PixelHeight);
        }


        public uint End
        {
            get { return Offset + CompressedSize; }
        }
    }

    public sealed class GrpFile : IDisposable
    {
        
        public GrpFile(Stream ndxFile, Stream grpFile, bool ownStreams)
        {
            if (ndxFile == null || grpFile == null) throw new ArgumentNullException();
            byte[] entryData = new byte[100];
            entries = new List<NdxEntry>();
            while (ndxFile.Read(entryData, 0, entryData.Length) == 100)
            {
                entries.Add(new NdxEntry(entryData));
            }

            NdxEntry[] sortedEntries = entries.ToArray();
            Array.Sort(sortedEntries, (a, b) => a.Offset.CompareTo(b.Offset));
            uint start = 0;
            for(int i=0; i<sortedEntries.Length; i++)
            {
                if(i < sortedEntries.Length-1 && sortedEntries[i].End > sortedEntries[i+1].Offset)
                {
                throw new InvalidDataException("The .ndx file contains overlapping entries.");
                }
                if(sortedEntries[i].Offset > start) grpLayout.AddLast(new NdxEntry(start, sortedEntries[i].Offset-start));
                grpLayout.AddLast(sortedEntries[i]);
                start = sortedEntries[i].End;
            }
            if(start < grpFile.Length) grpLayout.AddLast(new NdxEntry(start, (uint)(grpFile.Length - start)));
            else if(start > grpFile.Length) throw new InvalidDataException("The .ndx file references data not contained within the .grp file.");

            this.grpStream = grpFile;
            this.ndxStream = ndxFile;
            this.ownStreams = ownStreams;

            wasModified = false;
        }

        public IList<NdxEntry> IndexEntries { get { return entries.AsReadOnly(); } }

        public Stream OpenFile(NdxEntry entry)
        {
            return new PKWareDCLStream(new StreamStream(grpStream, entry.Offset, entry.CompressedSize, true), CompressionMode.Decompress);
        }
        
        public void Dispose()
        {
            if (ownStreams)
            {
                grpStream.Dispose();
                ndxStream.Dispose();
            }
        }
        
        

        public void Add(string fileName, Stream file, uint pixelWidth, uint pixelHeight)
        {
            file.Position = 0;

            if(fileName == null || file == null) throw new ArgumentNullException();

            if(string.IsNullOrEmpty(fileName) || !file.CanRead || !file.CanSeek || file.Length > int.MaxValue) throw new ArgumentException();

            // if the uncompressed file is larger than 512k, compress it on disk rather than in memory
            string tempFileName = file.Length > 512*1024 ? Path.GetTempFileName() : null;
            try
            {
                using(Stream temp = tempFileName == null ? (Stream)new MemoryStream((int)file.Length/2) : File.Open(tempFileName, FileMode.Create))
                {
                    uint size = (uint)file.Length, compressedSize;
                    using(PKWareDCLStream compressed = new PKWareDCLStream(temp, CompressionMode.Compress, false)) file.CopyTo(compressed);
                    if(temp.Length > int.MaxValue) throw new ArgumentException("The compressed file was too large.");
                    compressedSize = (uint)temp.Length;

                    NdxEntry entry = entries.FirstOrDefault(e => string.Equals(fileName, e.Name, StringComparison.OrdinalIgnoreCase));
                    if(entry != null) Unlink(entry);

                    // find the smallest free block that can hold it, if any
                    LinkedListNode<NdxEntry> freeNode = null;
                    for(LinkedListNode<NdxEntry> node = grpLayout.First; node != null; node = node.Next)
                    {
                        if(node.Value.Name == null && node.Value.CompressedSize >= compressedSize &&
                        (freeNode == null || node.Value.CompressedSize < freeNode.Value.CompressedSize))
                        {
                        freeNode = node;
                        }
                    }
                    if(freeNode == null) // if no free block could hold it...
                    {
                        freeNode = grpLayout.Last;
                        if(freeNode != null)
                        {
                        if(freeNode.Value.Name != null) freeNode = grpLayout.AddLast(new NdxEntry(freeNode.Value.End, compressedSize));
                        }
                        else
                        {
                        freeNode = grpLayout.AddLast(new NdxEntry(0, compressedSize));
                        }
                    }

                    if(freeNode.Value.CompressedSize > compressedSize)
                    {
                        grpLayout.AddAfter(freeNode, new NdxEntry(freeNode.Value.Offset+compressedSize, freeNode.Value.CompressedSize-compressedSize));
                    }

                    grpStream.Position = freeNode.Value.Offset;
                    temp.CopyTo(grpStream, true);

                    freeNode.Value.Name = fileName;
                    freeNode.Value.CompressedSize   = compressedSize;
                    freeNode.Value.UncompressedSize = size;
                    freeNode.Value.PixelWidth  = pixelWidth;
                    freeNode.Value.PixelHeight = pixelHeight;
                    entries.Add(freeNode.Value);
                }
            }
            finally
            {

            }

            // if (string.IsNullOrEmpty(fileName) || file == null) throw new ArgumentNullException();
            // if (fileName.Length > 79) throw new ArgumentException("Name too long");

            // NdxEntry existing = entries.FirstOrDefault(e => e.Name.Equals(fileName, StringComparison.OrdinalIgnoreCase));
            // if (existing != null) Unlink(existing);

            // byte[] buffer = new byte[file.Length];
            // file.Read(buffer, 0, buffer.Length);
            // MemoryStream ms = new MemoryStream();
            // using (PKWareDCLStream compressor = new PKWareDCLStream(ms, CompressionMode.Compress, true))
            // {
            //     compressor.Write(buffer, 0, buffer.Length);
            // }
        
            // ms.Position = 0;

            // uint offset = (uint)grpStream.Length;
            // grpStream.Position = offset;
            // ms.CopyTo(grpStream);

            // NdxEntry entry = new NdxEntry(offset, (uint)ms.Length)
            // {
            //     Name = fileName,
            //     UncompressedSize = (uint)file.Length,
            //     PixelWidth = pixelWidth,
            //     PixelHeight = pixelHeight
            // };
            // entries.Add(entry);
            // entries.Sort((a, b) => string.Compare(a.Name, b.Name, StringComparison.OrdinalIgnoreCase));
            // wasModified = true;
        }

        public void Unlink(NdxEntry entry)
        {
            if (entry == null) throw new ArgumentNullException();
            if(entries.Remove(entry))
            {
                LinkedListNode<NdxEntry> node = grpLayout.Find(entry), prev = node.Previous, next = node.Next;
                if(prev != null && prev.Value.Name == null)
                {
                prev.Value.CompressedSize += entry.CompressedSize;
                if(next != null && next.Value.Name == null)
                {
                    prev.Value.CompressedSize += next.Value.CompressedSize;
                    grpLayout.Remove(next);
                }
                }
                else if(next != null && next.Value.Name == null)
                {
                next.Value.CompressedSize += entry.CompressedSize;
                }
                else
                {
                grpLayout.AddAfter(node, new NdxEntry(entry.Offset, entry.CompressedSize));
                }
                grpLayout.Remove(node);
                wasModified = true;
            }
            
        }

        public void Repack()
        {
            



            // List<byte[]> buffers = new List<byte[]>();
            // foreach (NdxEntry entry in entries)
            // {
            //     grpStream.Position = entry.Offset;
            //     byte[] buffer = new byte[entry.CompressedSize];
            //     grpStream.Read(buffer, 0, buffer.Length);
            //     buffers.Add(buffer);
            // }

            // grpStream.SetLength(0);
            // for (int i = 0; i < entries.Count; i++)
            // {
            //     NdxEntry entry = entries[i];
            //     entry.Offset = (uint)grpStream.Position;
            //     grpStream.Write(buffers[i], 0, buffers[i].Length);
            // }
            if(grpLayout.Any(e => e.Name == null))
            {
                repack = true;
                wasModified = true;
            } 
        }

        public void Save()
        {
            if (!wasModified) return;
      
            
            if(repack)
            {
                Console.WriteLine("重新打包...");
                if(grpLayout.Any(e => e.Name == null))
                {
                    byte[] buffer = null;
                    uint offset = 0;
                    for(LinkedListNode<NdxEntry> node = grpLayout.First; node != null; )
                    {
                    LinkedListNode<NdxEntry> nextNode = node.Next;
                    NdxEntry entry = node.Value;
                    if(entry.Name == null)
                    {
                        grpLayout.Remove(entry);
                    }
                    else
                    {
                        if(entry.Offset != offset)
                        {
                            grpStream.Position = entry.Offset;
                            if(buffer == null || buffer.Length < entry.CompressedSize) buffer = new byte[entry.CompressedSize];
                            grpStream.ReadOrThrow(buffer, 0, (int)entry.CompressedSize);
                            grpStream.Position = offset;
                            grpStream.Write(buffer, 0, (int)entry.CompressedSize);
                            entry.Offset = offset;

                        }
                        offset += entry.CompressedSize;
                    }

                    node = nextNode;
                    }
                    grpStream.SetLength(offset);
                }
                repack = false;
            }
            else // if we're not going to repack, see if we can easily truncate the file
            {
                LinkedListNode<NdxEntry> node = grpLayout.Last;
                if(node != null && node.Value.Name == null)
                {
                    grpStream.SetLength(node.Value.Offset);
                    grpLayout.Remove(node);
                }
            }

            NdxEntry[] sortedEntries = entries.ToArray();
            Array.Sort(sortedEntries, (a, b) => string.Compare(a.Name, b.Name, true));

            ndxStream.Position = 0;
            ndxStream.SetLength(sortedEntries.Length * 100);
            byte[] data = new byte[100];
            foreach(NdxEntry entry in sortedEntries)
            {
                entry.Save(data);
                ndxStream.Write(data);
            }
            
   

            // ndxStream.SetLength(0);
            // foreach (NdxEntry entry in entries)
            // {
            //     byte[] data = entry.ToByteArray();
            //     ndxStream.Write(data, 0, data.Length);
            // }
            // ndxStream.Flush();
            // grpStream.Flush();
            // wasModified = false;
        }

        public bool WasModified { get { return wasModified; } }
        private readonly List<NdxEntry> entries;

        readonly LinkedList<NdxEntry> grpLayout = new LinkedList<NdxEntry>();

        private readonly Stream grpStream, ndxStream;
        private readonly bool ownStreams;

        private bool wasModified;

        bool repack;
    }
}