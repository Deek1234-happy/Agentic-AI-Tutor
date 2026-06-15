import { useCallback, useRef, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { X, ZoomIn, ZoomOut, Target } from "lucide-react";
import { Button } from "../ui/button";
import type { KnowledgeGraphContext } from "../../../types/chat";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "../ui/dialog";

interface KnowledgeGraphViewerProps {
  kgContext: KnowledgeGraphContext;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function KnowledgeGraphViewer({ kgContext, open, onOpenChange }: KnowledgeGraphViewerProps) {
  const fgRef = useRef<any>(null);

  // Transform data to what react-force-graph expects
  const graphData = {
    nodes: kgContext.entities.map((n) => ({ id: n.id, name: n.label || n.name, val: 1 })),
    links: kgContext.relationships.map((e) => ({ source: e.source, target: e.target, name: e.relation || e.type || e.label })),
  };

  useEffect(() => {
    if (open && fgRef.current) {
      setTimeout(() => {
        fgRef.current.zoomToFit(800, 100);
      }, 200);
    }
  }, [open, kgContext]);

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.name || "Unknown";
    const fontSize = 12 / globalScale;
    ctx.font = `600 ${fontSize}px Inter, sans-serif`;
    const textWidth = ctx.measureText(label).width;
    const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.8);

    const radius = 6 / globalScale;
    
    // Draw Node Circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
    ctx.fillStyle = "#3b82f6"; // primary blue
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5 / globalScale;
    ctx.stroke();

    // Draw Label Background
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.beginPath();
    const bgX = node.x - bckgDimensions[0] / 2;
    const bgY = node.y + radius + (4 / globalScale);
    ctx.roundRect(bgX, bgY, bckgDimensions[0], bckgDimensions[1], 4 / globalScale);
    ctx.fill();
    
    // Draw Label Text
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#1e293b"; // slate-800
    ctx.fillText(label, node.x, bgY + bckgDimensions[1] / 2);

    node.__bckgDimensions = bckgDimensions;
  }, []);

  const paintLink = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const start = link.source;
    const end = link.target;
    if (typeof start !== "object" || typeof end !== "object") return;

    const label = link.name;
    const fontSize = 10 / globalScale;
    ctx.font = `${fontSize}px Inter, sans-serif`;
    
    const textPos = {
      x: start.x + (end.x - start.x) / 2,
      y: start.y + (end.y - start.y) / 2,
    };
    
    const textWidth = ctx.measureText(label).width;
    
    // Background pill for link label
    ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
    ctx.beginPath();
    ctx.roundRect(
      textPos.x - textWidth / 2 - 4 / globalScale,
      textPos.y - fontSize / 2 - 2 / globalScale,
      textWidth + 8 / globalScale,
      fontSize + 4 / globalScale,
      4 / globalScale
    );
    ctx.fill();

    ctx.fillStyle = "#64748b"; // slate-500
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, textPos.x, textPos.y);
  }, []);

  const handleZoomIn = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom * 1.5, 400);
    }
  };

  const handleZoomOut = () => {
    if (fgRef.current) {
      const currentZoom = fgRef.current.zoom();
      fgRef.current.zoom(currentZoom / 1.5, 400);
    }
  };

  const handleFit = () => {
    if (fgRef.current) fgRef.current.zoomToFit(400, 100);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!fixed !inset-0 !translate-x-0 !translate-y-0 !max-w-none !w-screen !h-[100dvh] !m-0 !p-0 !rounded-none !border-0 flex flex-col bg-slate-50 data-[state=open]:slide-in-from-bottom-full data-[state=closed]:slide-out-to-bottom-full duration-500 overflow-hidden [&>button]:hidden">
        
        {/* Premium Dotted Canvas Background */}
        <div className="absolute inset-0 pointer-events-none opacity-40" style={{ backgroundImage: "radial-gradient(#94a3b8 1.5px, transparent 1.5px)", backgroundSize: "28px 28px" }} />
        <DialogTitle className="sr-only">Knowledge Graph Fullscreen Viewer</DialogTitle>
        <DialogDescription className="sr-only">Interactive visualization of AI relationships</DialogDescription>
        
        {/* Floating Header Overlay */}
        <div className="absolute top-6 left-6 right-6 z-50 flex items-center justify-between pointer-events-none">
          <div className="bg-white/90 backdrop-blur-md shadow-sm border border-slate-200/50 px-5 py-3 rounded-2xl flex items-center gap-3 pointer-events-auto">
            <div className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
            <h2 className="font-semibold text-slate-800 tracking-tight text-sm">Knowledge Graph</h2>
            <span className="bg-slate-100 text-slate-600 text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full ml-2">
              {graphData.nodes.length} Entities
            </span>
          </div>
          
          <div className="flex items-center gap-1.5 bg-white/90 backdrop-blur-md shadow-sm border border-slate-200/50 p-1.5 rounded-2xl pointer-events-auto">
            <Button variant="ghost" size="icon" onClick={handleZoomOut} className="h-9 w-9 rounded-xl hover:bg-slate-100">
              <ZoomOut className="w-4 h-4 text-slate-700" />
            </Button>
            <Button variant="ghost" size="icon" onClick={handleZoomIn} className="h-9 w-9 rounded-xl hover:bg-slate-100">
              <ZoomIn className="w-4 h-4 text-slate-700" />
            </Button>
            <Button variant="ghost" size="icon" onClick={handleFit} className="h-9 w-9 rounded-xl hover:bg-slate-100">
              <Target className="w-4 h-4 text-slate-700" />
            </Button>
            <div className="w-px h-5 bg-slate-200 mx-1.5" />
            <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)} className="h-9 w-9 rounded-xl hover:bg-red-50 hover:text-red-600">
              <X className="w-4.5 h-4.5" />
            </Button>
          </div>
        </div>
        
        <div className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing">
          {open && (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              nodeCanvasObject={paintNode}
              nodePointerAreaPaint={(node: any, color, ctx) => {
                ctx.fillStyle = color;
                const bckgDimensions = node.__bckgDimensions;
                if (bckgDimensions) {
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI, false);
                  ctx.fill();
                  ctx.fillRect(
                    node.x - bckgDimensions[0] / 2,
                    node.y + 6,
                    bckgDimensions[0],
                    bckgDimensions[1]
                  );
                }
              }}
              linkCanvasObjectMode={() => "after"}
              linkCanvasObject={paintLink}
              linkColor={() => "#cbd5e1"}
              linkWidth={1.5}
              linkDirectionalParticles={2}
              linkDirectionalParticleSpeed={0.005}
              linkDirectionalParticleWidth={2}
              linkDirectionalParticleColor={() => "#3b82f6"}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              onNodeDragEnd={(node) => {
                node.fx = node.x;
                node.fy = node.y;
              }}
              cooldownTicks={100}
              d3VelocityDecay={0.3}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
