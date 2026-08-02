import UploadContainer from '@/components/upload/UploadContainer';

export const metadata = {
  title: 'Upload Document — Matilda',
  description: 'Upload a document or manuscript to analyze attribution issues and historical provenance.',
};

export default function UploadPage() {
  return (
    <div className="flex-1 bg-[#FAF8F5] flex items-center justify-center">
      <UploadContainer />
    </div>
  );
}
