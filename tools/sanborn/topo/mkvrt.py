import rasterio, glob, os
fs=sorted(glob.glob('warped/Sheet_*_1912_EPSG26916.tif')); R=0.5
B={}
for f in fs:
    with rasterio.open(f) as s: B[f]=(s.bounds,s.width,s.height,s.crs.to_wkt())
e0=min(b[0].left for b in B.values()); e1=max(b[0].right for b in B.values()); n0=min(b[0].bottom for b in B.values()); n1=max(b[0].top for b in B.values())
W=int(round((e1-e0)/R)); H=int(round((n1-n0)/R)); wkt=next(iter(B.values()))[3]
L=[f'<VRTDataset rasterXSize="{W}" rasterYSize="{H}">',f'  <SRS>{wkt}</SRS>',f'  <GeoTransform>{e0}, {R}, 0, {n1}, 0, {-R}</GeoTransform>']
for band,ci in ((1,'Red'),(2,'Green'),(3,'Blue')):
    L.append(f'  <VRTRasterBand dataType="Byte" band="{band}"><ColorInterp>{ci}</ColorInterp>')
    for f,(b,w,h,_) in B.items():
        x=int(round((b.left-e0)/R)); y=int(round((n1-b.top)/R))
        L.append(f'    <ComplexSource><SourceFilename relativeToVRT="1">{os.path.basename(f)}</SourceFilename><SourceBand>{band}</SourceBand>'
                 f'<SrcRect xOff="0" yOff="0" xSize="{w}" ySize="{h}"/><DstRect xOff="{x}" yOff="{y}" xSize="{w}" ySize="{h}"/><UseMaskBand>true</UseMaskBand></ComplexSource>')
    L.append('  </VRTRasterBand>')
L.append('  <MaskBand><VRTRasterBand dataType="Byte">')
for f,(b,w,h,_) in B.items():
    x=int(round((b.left-e0)/R)); y=int(round((n1-b.top)/R))
    L.append(f'    <ComplexSource><SourceFilename relativeToVRT="1">{os.path.basename(f)}</SourceFilename><SourceBand>mask,1</SourceBand>'
             f'<SrcRect xOff="0" yOff="0" xSize="{w}" ySize="{h}"/><DstRect xOff="{x}" yOff="{y}" xSize="{w}" ySize="{h}"/></ComplexSource>')
L.append('  </VRTRasterBand></MaskBand>'); L.append('</VRTDataset>')
open('warped/1912_Survey_Mosaic.vrt','w').write('\n'.join(L)); print(W,H)
