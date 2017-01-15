require "formula" 
 
class TrainScanner < Formula 
  homepage "https://github.com/vitroid/TrainScanner" 
  url "https://github.com/vitroid/TrainScanner/archive/v3.6.002.tar.gz" 
  sha1 "a759c411891701b3b18d89cc297077b73c12bfa4" 
 
  depends_on "pyqt5"
  depends_on "python3"
  depends_on "opencv3" => ["with-ffmpeg", "with-tbb", "with-python3", "HEAD"]
 
  def install 
    system "make", "all" 
  end 
 
  test do 
    system "false" 
  end 
end 
