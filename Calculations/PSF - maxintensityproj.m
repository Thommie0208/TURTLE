function [proj] = maxintensityproj(I, ndir)
% Maximum intensity projection along one dimension given by ndir of a 
% 3D image
% Input Parameters:
% ----------------
% 3D Image
%%Example usage:
% -------------
%%Projection along XY plane
% Ixy = maxintensityproj(I, 3);
% figure, imagesc(Ixy);
%%Projection along XZ plane
% Ixz = maxintensityproj(I, 1);
% figure, imagesc(Ixz');
% 
% Author: Praveen Pankajakshan
% Email: praveen.pankaj@gmail.com
% Last modified: June 24, 2011 17:21
% Copyright (C) 2011 Praveen Pankajakshan
% All rights reserved.
% Redistribution and use in source and binary forms, with or without 
% modification, are permitted provided that the following conditions are met:
% 1. Redistributions of source code must retain the above copyright notice, 
% this list of conditions and the following disclaimer.
% 2. Redistributions in binary form must reproduce the above copyright notice, 
% this list of conditions and the following disclaimer in the documentation 
% and/or other materials provided with the distribution.
% THIS SOFTWARE IS PROVIDED BY <COPYRIGHT HOLDER> ``AS IS'' AND ANY EXPRESS OR 
% IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
% MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO 
% EVENT SHALL <COPYRIGHT HOLDER> OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
% INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
% BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
% DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
% ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
% (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
% SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
% The views and conclusions contained in the software and documentation are those 
% of the authors and should not be interpreted as representing official policies, 
% either expressed or implied, of Praveen Pankajakshan.
%
if size(I, 3)<2
    error(['Input image is not a volume. Works only on images where ', ...
        'the third dimension size is greater than one.']);
end
proj(:, :) = max(I, [], ndir);
