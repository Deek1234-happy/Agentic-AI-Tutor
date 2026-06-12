import { useParams, Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../context/AuthContext";
import { getSubjectById } from "../../services/subjectService";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { ArrowLeft, FileText } from "lucide-react";
import DocumentsTab from "../components/subject/DocumentsTab";

export default function SubjectDetail() {
  const { subjectId } = useParams<{ subjectId: string }>();
  const { session } = useAuth();

  // Fetch the real subject name from GET /api/Subject/{id}
  const { data: subject, isLoading } = useQuery({
    queryKey: ["subject", subjectId],
    queryFn: () => getSubjectById(subjectId!),
    enabled: !!session && !!subjectId,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/dashboard/subjects">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Subjects
          </Button>
        </Link>

        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center">
            <FileText className="w-8 h-8 text-primary-foreground" />
          </div>
          <div>
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-48 mb-2" />
                <Skeleton className="h-4 w-56" />
              </>
            ) : (
              <>
                <h1 className="text-3xl mb-1 capitalize">{subject?.name ?? "Subject"}</h1>
                <p className="text-muted-foreground">Manage documents and track progress</p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Content — only render if we have a real subjectId */}
      {subjectId && (
        <div className="mt-6">
          {/* DocumentsTab receives the subjectId so it can enforce subject-scoped fetching & upload */}
          <DocumentsTab subjectId={subjectId} />
        </div>
      )}
    </div>
  );
}